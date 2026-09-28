import { nanoid } from "nanoid";
import { db } from "./db.js";
import { config } from "./config.js";
import type { Inbound, Protocol, Transport } from "./types.js";

interface SeedDef {
  tag: string;
  protocol: Protocol;
  transport: Transport;
}

const SEED_INBOUNDS: SeedDef[] = [
  { tag: "VLESS-WS", protocol: "vless", transport: "ws" },
  { tag: "VLESS-XHTTP", protocol: "vless", transport: "xhttp" },
  { tag: "VMess-WS", protocol: "vmess", transport: "ws" },
  { tag: "Trojan-WS", protocol: "trojan", transport: "ws" },
  { tag: "VLESS-HTTPUpgrade", protocol: "vless", transport: "httpupgrade" },
];

export function seedInbounds(): void {
  const count = (db.prepare("SELECT COUNT(*) AS c FROM inbounds").get() as { c: number }).c;
  if (count > 0) return;
  let offset = 0;
  const insert = db.prepare(
    `INSERT INTO inbounds (tag, label, protocol, transport, port, path, host, enabled, created_at)
     VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?)`,
  );
  for (const s of SEED_INBOUNDS) {
    const port = config.inboundBasePort + offset;
    const path = `/SideRail/${s.transport}-${nanoid(8)}`;
    insert.run(s.tag, s.tag, s.protocol, s.transport, port, path, "", Date.now());
    offset += 1;
  }
}

export function listInbounds(): Inbound[] {
  return db.prepare("SELECT * FROM inbounds ORDER BY id ASC").all() as unknown as Inbound[];
}

export function listEnabledInbounds(): Inbound[] {
  return db
    .prepare("SELECT * FROM inbounds WHERE enabled = 1 ORDER BY id ASC")
    .all() as unknown as Inbound[];
}

export function getInbound(id: number): Inbound | undefined {
  return db.prepare("SELECT * FROM inbounds WHERE id = ?").get(id) as unknown as
    | Inbound
    | undefined;
}

export function setInboundEnabled(id: number, enabled: boolean): void {
  db.prepare("UPDATE inbounds SET enabled = ? WHERE id = ?").run(enabled ? 1 : 0, id);
}

/** ── وصلهٔ ما ────────────────────────────────────────────────────────────────
 *  مسیرِ اینباند: هر مسیری مجاز است به‌شرطِ اینکه:
 *    • با «/» شروع و با حرف/عدد شروع شود، ۱..۴ بخش، بدونِ نویسهٔ عجیب
 *    • رزروشده نباشد: /api · /sub · /assets · /favicon · /healthz (این‌ها را خودِ اپ می‌خواهد)
 *  نیازی نیست «SideRail» در مسیر باشد — منطقِ تونل (tunnel.ts → matchInbound)
 *  فقط تطبیقِ دقیق/پیشوندی با همان مسیر را چک می‌کند.
 */
export function normalizeInboundPath(
  input: string,
): { ok: true; path: string } | { ok: false; error: string } {
  let p = String(input || "").trim();
  if (!p.startsWith("/")) p = "/" + p;
  p = p.replace(/\/+$/, "");
  if (p.length < 2 || p.length > 64) return { ok: false, error: "path length must be 2..64" };
  if (!/^\/[A-Za-z0-9][A-Za-z0-9/_.~-]*$/.test(p))
    return { ok: false, error: "path may only contain letters, digits and / _ . ~ -" };
  if (p.split("/").length > 5) return { ok: false, error: "path is too deep" };
  const reserved = ["/api", "/sub", "/assets", "/favicon", "/healthz"];
  if (reserved.some((r) => p === r || p.startsWith(r + "/")))
    return { ok: false, error: "path is reserved by the panel" };
  return { ok: true, path: p };
}

/** ویرایشِ نامِ نمایشی/تگ/مسیرِ اینباند (نامِ کانفیگِ کاربران از همین می‌آید). */
export function updateInbound(
  id: number,
  patch: { tag?: string; label?: string; path?: string },
): { ok: true; changed: string[] } | { ok: false; error: string } {
  const ib = getInbound(id);
  if (!ib) return { ok: false, error: "inbound not found" };
  const sets: string[] = [];
  const vals: (string | number)[] = [];
  const changed: string[] = [];

  if (patch.tag !== undefined) {
    const tag = String(patch.tag).trim();
    if (!/^[A-Za-z0-9 _.-]{1,32}$/.test(tag))
      return { ok: false, error: "tag may only contain letters, digits, space, _ . -  (1..32)" };
    const dup = db
      .prepare("SELECT id FROM inbounds WHERE tag = ? AND id <> ?")
      .get(tag, id) as { id: number } | undefined;
    if (dup) return { ok: false, error: "tag already exists" };
    if (tag !== ib.tag) {
      sets.push("tag = ?");
      vals.push(tag);
      changed.push("tag");
    }
  }

  if (patch.label !== undefined) {
    const label = String(patch.label).trim();
    if (label.length > 48) return { ok: false, error: "label must be at most 48 characters" };
    if (label !== ib.label) {
      sets.push("label = ?");
      vals.push(label);
      changed.push("label");
    }
  }

  if (patch.path !== undefined) {
    const norm = normalizeInboundPath(patch.path);
    if (!norm.ok) return { ok: false, error: norm.error };
    const dup = db
      .prepare("SELECT id FROM inbounds WHERE path = ? AND id <> ?")
      .get(norm.path, id) as { id: number } | undefined;
    if (dup) return { ok: false, error: "path already used by another inbound" };
    if (norm.path !== ib.path) {
      sets.push("path = ?");
      vals.push(norm.path);
      changed.push("path");
    }
  }

  if (sets.length === 0) return { ok: true, changed: [] };
  vals.push(id);
  db.prepare(`UPDATE inbounds SET ${sets.join(", ")} WHERE id = ?`).run(...(vals as never[]));
  return { ok: true, changed };
}
