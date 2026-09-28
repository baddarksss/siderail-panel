/**
 * SideRail - Xray-core VPN management panel
 * Copyright (c) 2025 icubaby. All rights reserved.
 * Official repository: https://github.com/icubaby/SideRail
 *
 * Licensed under the SideRail Proprietary License (see LICENSE).
 * Unauthorized selling, white-labeling, or removal of attribution,
 * branding, or the embedded authorship identifiers is prohibited.
 * Watermark: sr-icubaby-2025-9f4c1a7e
 */
/**
 * 🔑 توکنِ دسترسیِ ماشین (رباتِ مدیریت)
 *
 * چرا: رباتِ بیرونی برای کار با این پنل تا حالا به «آدرس + نام‌کاربری + رمز»
 * نیاز داشت. با این توکن، فقط یک رشتهٔ کوتاه لازم است و خودِ توکن آدرسِ عمومیِ
 * همین پنل را هم در خودش دارد ⇒ ربات بدونِ پرسیدنِ چیزی همه را می‌خواند.
 *
 * شکلِ توکن:  srb1.<base64url({u:آدرس,n:نام,t:زمان})>.<id>.<secret>
 *   • `u` = آدرسِ عمومیِ پنل (https) — همان چیزی که ادمین در مرورگر باز کرده
 *   • `n` = نامِ نمایشیِ دلخواه (برای شناسایی در ربات)
 *   • رازِ اصلی فقط در ستونِ hash ذخیره می‌شود (sha256) — فایلِ دیتابیس راز را لو نمی‌دهد
 *
 * این توکن همان مسیرِ JWT را در `authGuard` رد می‌کند (Authorization: Bearer)،
 * پس روی همهٔ مسیرهای /api کار می‌کند.
 */
import crypto from "node:crypto";
import { db } from "./db.js";

export const API_TOKEN_PREFIX = "srb1.";

interface TokenRow {
  id: number;
  name: string;
  prefix: string;
  hash: string;
  created_at: number;
  last_used_at: number;
  used_count: number;
  revoked_at: number | null;
}

export interface ApiTokenInfo {
  id: number;
  name: string;
  prefix: string;
  createdAt: number;
  lastUsedAt: number;
  usedCount: number;
  revokedAt: number | null;
}

export function migrateApiTokens(): void {
  db.exec(`
    CREATE TABLE IF NOT EXISTS api_tokens (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      name TEXT NOT NULL DEFAULT '',
      prefix TEXT NOT NULL DEFAULT '',
      hash TEXT NOT NULL,
      created_at INTEGER NOT NULL,
      last_used_at INTEGER NOT NULL DEFAULT 0,
      used_count INTEGER NOT NULL DEFAULT 0,
      revoked_at INTEGER
    );
    CREATE INDEX IF NOT EXISTS idx_api_tokens_hash ON api_tokens(hash);
  `);
}

const sha256 = (s: string): string => crypto.createHash("sha256").update(s).digest("hex");

/** آدرسِ عمومیِ پنل از روی همان درخواستی که ادمین با آن توکن می‌سازد. */
export function originFromHeaders(headers: Record<string, unknown>): string {
  const protoRaw = String(headers["x-forwarded-proto"] || "https").split(",")[0].trim().replace(/:$/, "");
  const proto = protoRaw === "http" ? "http" : "https";
  const host = String(headers["x-forwarded-host"] || headers.host || "").split(",")[0].trim();
  if (!host) return "";
  if (!/^[a-z0-9.\-:\[\]]+$/i.test(host)) return "";
  return `${proto}://${host}`;
}

function toInfo(row: TokenRow): ApiTokenInfo {
  return {
    id: row.id,
    name: row.name,
    prefix: row.prefix,
    createdAt: row.created_at,
    lastUsedAt: row.last_used_at,
    usedCount: row.used_count,
    revokedAt: row.revoked_at,
  };
}

export function listApiTokens(): ApiTokenInfo[] {
  const rows = db
    .prepare("SELECT * FROM api_tokens ORDER BY id DESC")
    .all() as unknown as TokenRow[];
  return rows.map(toInfo);
}

/** ساختِ توکنِ تازه — رشتهٔ کامل فقط همین یک‌بار برگردانده می‌شود. */
export function createApiToken(
  name: string,
  origin: string,
): { ok: boolean; token?: string; info?: ApiTokenInfo; error?: string } {
  if (!origin) return { ok: false, error: "public url could not be detected" };
  const clean = String(name || "").trim().slice(0, 40) || "bot";
  const secret = crypto.randomBytes(24).toString("base64url");
  const createdAt = Date.now();
  const res = db
    .prepare(
      "INSERT INTO api_tokens (name, prefix, hash, created_at, last_used_at, used_count) VALUES (?, ?, ?, ?, 0, 0)",
    )
    .run(clean, secret.slice(0, 6), sha256(secret), createdAt);
  const id = Number(res.lastInsertRowid);
  const payload = Buffer.from(
    JSON.stringify({ u: origin, n: clean, t: createdAt }),
    "utf8",
  ).toString("base64url");
  const token = `${API_TOKEN_PREFIX}${payload}.${id}.${secret}`;
  const row = db.prepare("SELECT * FROM api_tokens WHERE id = ?").get(id) as unknown as TokenRow;
  return { ok: true, token, info: toInfo(row) };
}

export function revokeApiToken(id: number): { ok: boolean; error?: string } {
  const row = db.prepare("SELECT id, revoked_at FROM api_tokens WHERE id = ?").get(id) as
    | { id: number; revoked_at: number | null }
    | undefined;
  if (!row) return { ok: false, error: "not found" };
  if (!row.revoked_at) db.prepare("UPDATE api_tokens SET revoked_at = ? WHERE id = ?").run(Date.now(), id);
  return { ok: true };
}

export function deleteApiToken(id: number): { ok: boolean; error?: string } {
  const row = db.prepare("SELECT id FROM api_tokens WHERE id = ?").get(id);
  if (!row) return { ok: false, error: "not found" };
  db.prepare("DELETE FROM api_tokens WHERE id = ?").run(id);
  return { ok: true };
}

/** اعتبارسنجیِ توکن (بدونِ افشای راز در حافظهٔ موقت). */
export function verifyApiToken(raw: string): { ok: boolean; id?: number; name?: string } {
  const s = String(raw || "").trim();
  if (!s.startsWith(API_TOKEN_PREFIX)) return { ok: false };
  const parts = s.split(".");
  if (parts.length !== 4) return { ok: false };
  const id = Number(parts[2]);
  const secret = parts[3];
  if (!Number.isInteger(id) || id <= 0 || !secret) return { ok: false };
  const row = db.prepare("SELECT * FROM api_tokens WHERE id = ?").get(id) as unknown as TokenRow | undefined;
  if (!row || row.revoked_at) return { ok: false };
  const a = Buffer.from(row.hash, "hex");
  const b = Buffer.from(sha256(secret), "hex");
  if (a.length !== b.length || a.length === 0 || !crypto.timingSafeEqual(a, b)) return { ok: false };
  return { ok: true, id: row.id, name: row.name };
}

/** شمارندهٔ استفاده — آخرین‌استفاده حداکثر هر ۵ دقیقه یک‌بار نوشته می‌شود. */
export function touchApiToken(id: number): void {
  try {
    const now = Date.now();
    db.prepare(
      "UPDATE api_tokens SET used_count = used_count + 1, last_used_at = CASE WHEN last_used_at < ? THEN ? ELSE last_used_at END WHERE id = ?",
    ).run(now - 300000, now, id);
  } catch {
    /* noop — نبودِ آمار نباید جلوی درخواست را بگیرد */
  }
}

/**
 * خلاصهٔ پنل برای «دست‌دادنِ» ربات: هر چیزی که ربات برای شناختنِ پنل لازم دارد
 * با یک درخواست خوانده می‌شود (نام، آدرس، اینباندها، شمارشِ کاربران، ترافیک).
 */
export function panelHandshake(origin: string): Record<string, unknown> {
  const inbounds = db
    .prepare("SELECT id, tag, label, protocol, transport, port, enabled FROM inbounds ORDER BY id ASC")
    .all() as unknown as Record<string, unknown>[];
  const users = db
    .prepare(
      "SELECT COUNT(*) AS total, COALESCE(SUM(CASE WHEN enabled = 1 THEN 1 ELSE 0 END), 0) AS enabled FROM users",
    )
    .get() as { total: number; enabled: number };
  const traffic = db
    .prepare("SELECT COALESCE(SUM(up), 0) AS up, COALESCE(SUM(down), 0) AS down FROM users")
    .get() as { up: number; down: number };
  return {
    ok: true,
    app: "SideRail",
    version: process.env.PANEL_VERSION || "2.3.0",
    url: origin,
    time: Date.now(),
    inbounds: inbounds.map((ib) => ({
      id: Number(ib.id),
      tag: String(ib.tag || ""),
      label: String(ib.label || ""),
      protocol: String(ib.protocol || ""),
      transport: String(ib.transport || ""),
      port: Number(ib.port) || 0,
      enabled: Number(ib.enabled) === 1,
    })),
    users: { total: Number(users.total) || 0, enabled: Number(users.enabled) || 0 },
    traffic: { up: Number(traffic.up) || 0, down: Number(traffic.down) || 0 },
  };
}
