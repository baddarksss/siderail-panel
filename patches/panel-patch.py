#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────────────────────
#  panel-patch.py — وصله‌های ما روی سورسِ SideRail (قابلِ اعمال روی هر نسخهٔ تازه)
#
#  چه می‌کند:
#   ۱) نامِ کانفیگ‌ها = «نامِ نمایشیِ اینباند» (label) یا همان tag — بدونِ پیشوندِ برند
#   ۲) عنوانِ سابسکریپشن دیگر «SideRail <email>» نیست؛ از تنظیمِ subTitle می‌آید
#      (خالی ⇒ فقط ایمیل) ⇒ اسمِ سابی که خودت در کلاینت می‌دهی می‌ماند
#   ۳) امکانِ ویرایشِ اینباند از پنل: نامِ نمایشی (label) · تگ (tag) · مسیر (path)
#   ۴) نامِ کاربرِ Clash/Sing-box هم از label می‌آید
#   ۵) مهاجرتِ خودکارِ دیتابیس (ستونِ label) — بدونِ از دست رفتنِ داده
#
#  اجرا:  python3 patches/panel-patch.py [--check] [--root /path/to/SideRail]
#  اعمال روی نسخهٔ تازهٔ upstream:  ./apply_upstream.sh
# ─────────────────────────────────────────────────────────────────────────────
import argparse, io, os, re, sys

ROOT = os.environ.get("SIDERAIL_ROOT", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
done, skipped = [], []

def read(rel):
    return io.open(os.path.join(ROOT, rel), encoding="utf-8").read()

def write(rel, txt):
    io.open(os.path.join(ROOT, rel), "w", encoding="utf-8").write(txt)

def sub(rel, old, new, label, count=1, required=True):
    txt = read(rel)
    n = txt.count(old)
    if n == count:
        if new is not None:
            write(rel, txt.replace(old, new, count))
        done.append(label)
    elif n == 0 and not required:
        skipped.append(label)
    else:
        print(f"❌ {label}: {n} تطبیق (انتظار {count}) — نسخهٔ upstream عوض شده؟ فایل: {rel}")
        sys.exit(1)

CHECK = "--check" in sys.argv
if CHECK:
    write = lambda rel, txt: None  # noqa: E731

# ۱) نوعِ Inbound ⇒ ستونِ label ───────────────────────────────────────────────
sub("apps/server/src/types.ts",
    "export interface Inbound {\n  id: number;\n  tag: string;\n",
    "export interface Inbound {\n  id: number;\n  tag: string;\n  /** نامِ نمایشیِ اینباند در کانفیگ‌ها (خالی ⇒ همان tag) */\n  label: string;\n",
    "types.ts: label در Inbound")

# ۲) مهاجرتِ دیتابیس ─────────────────────────────────────────────────────────
sub("apps/server/src/db.ts",
    "  const routingCols = db.prepare(\"PRAGMA table_info(routing_rules)\").all() as { name: string }[];",
    "  const inboundCols = db.prepare(\"PRAGMA table_info(inbounds)\").all() as { name: string }[];\n"
    "  if (!inboundCols.map((c) => c.name).includes(\"label\"))\n"
    "    db.exec(\"ALTER TABLE inbounds ADD COLUMN label TEXT NOT NULL DEFAULT ''\");\n\n"
    "  const routingCols = db.prepare(\"PRAGMA table_info(routing_rules)\").all() as { name: string }[];",
    "db.ts: مهاجرتِ ستونِ label")

# ۳) اینباندها: بذر با label + توابعِ ویرایش/اعتبارسنجیِ مسیر ─────────────────
sub("apps/server/src/inbounds.ts",
    "    `INSERT INTO inbounds (tag, protocol, transport, port, path, host, enabled, created_at)\n"
    "     VALUES (?, ?, ?, ?, ?, ?, 1, ?)`,",
    "    `INSERT INTO inbounds (tag, label, protocol, transport, port, path, host, enabled, created_at)\n"
    "     VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?)`,",
    "inbounds.ts: INSERT با label")
sub("apps/server/src/inbounds.ts",
    "    insert.run(s.tag, s.protocol, s.transport, port, path, \"\", Date.now());",
    "    insert.run(s.tag, s.tag, s.protocol, s.transport, port, path, \"\", Date.now());",
    "inbounds.ts: مقدارِ label در بذر")

UPDATE_CODE = '''
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
  p = p.replace(/\\/+$/, "");
  if (p.length < 2 || p.length > 64) return { ok: false, error: "path length must be 2..64" };
  if (!/^\\/[A-Za-z0-9][A-Za-z0-9/_.~-]*$/.test(p))
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
'''
# انتهای inbounds.ts (بعد از setInboundEnabled)
sub("apps/server/src/inbounds.ts",
    "export function setInboundEnabled(id: number, enabled: boolean): void {\n"
    "  db.prepare(\"UPDATE inbounds SET enabled = ? WHERE id = ?\").run(enabled ? 1 : 0, id);\n}\n",
    "export function setInboundEnabled(id: number, enabled: boolean): void {\n"
    "  db.prepare(\"UPDATE inbounds SET enabled = ? WHERE id = ?\").run(enabled ? 1 : 0, id);\n}\n" + UPDATE_CODE,
    "inbounds.ts: updateInbound + normalizeInboundPath")

# ۴) نامِ کانفیگ = label || tag (بدونِ پیشوندِ برند) ──────────────────────────
sub("apps/server/src/links.ts",
    "function label(inbound: Inbound): string {\n  return `icubaby/SideRail - ${inbound.tag}`;\n}",
    "function label(inbound: Inbound): string {\n"
    "  // وصلهٔ ما: نامِ کانفیگ = نامِ نمایشیِ اینباند (label)، وگرنه tag — بدونِ برند\n"
    "  return (inbound.label && inbound.label.trim()) || inbound.tag;\n}",
    "links.ts: نامِ کانفیگ")

# ۵) عنوانِ سابسکریپشن از تنظیمات (خالی ⇒ فقط ایمیل) ─────────────────────────
sub("apps/server/src/sub.ts",
    "import { db } from \"./db.js\";",
    "import { db, getSetting } from \"./db.js\";",
    "sub.ts: importِ getSetting")
sub("apps/server/src/sub.ts",
    "function subUserInfo(u: {",
    "function subProfileTitle(email: string): string {\n"
    "  // وصلهٔ ما: پیشوندِ برند حذف شد؛ اگر «عنوانِ ساب» در تنظیمات پر باشد، همان می‌آید\n"
    "  const title = (getSetting(\"sub_title\") || \"\").trim();\n"
    "  return title ? `${title} ${email}` : email;\n}\n\n"
    "function subUserInfo(u: {",
    "sub.ts: subProfileTitle")
sub("apps/server/src/sub.ts",
    "  res.setHeader(\"Profile-Title\", Buffer.from(`SideRail ${data.user.email}`).toString(\"base64\"));",
    "  res.setHeader(\"Profile-Title\", Buffer.from(subProfileTitle(data.user.email)).toString(\"base64\"));",
    "sub.ts: Profile-Title (clash)", count=2)

# ۶) Clash/Sing-box: نامِ پروفایل‌ها از label ───────────────────────────────
sub("apps/server/src/sub-formats.ts",
    "  const name = `${inbound.tag}`;",
    "  const name = (inbound.label && inbound.label.trim()) || inbound.tag; // وصلهٔ ما",
    "sub-formats.ts: نامِ پروکسی")
sub("apps/server/src/sub-formats.ts",
    "function singboxOutbound(ctx: Ctx): Record<string, unknown> | null {",
    "function subGroupName(): string {\n"
    "  const t = (getSetting(\"sub_title\") || \"\").trim();\n"
    "  return t || \"Proxy\";\n}\n\n"
    "function singboxOutbound(ctx: Ctx): Record<string, unknown> | null {",
    "sub-formats.ts: subGroupName")
sub("apps/server/src/sub-formats.ts",
    "  yaml.push(`  - name: SideRail`);",
    "  yaml.push(`  - name: ${JSON.stringify(subGroupName())}`);",
    "sub-formats.ts: نامِ گروهِ Clash")
sub("apps/server/src/sub-formats.ts",
    "  yaml.push(\"  - MATCH,SideRail\");",
    "  yaml.push(`  - MATCH,${subGroupName()}`);",
    "sub-formats.ts: قاعدهٔ MATCH")
sub("apps/server/src/sub-formats.ts",
    "        tag: \"SideRail\",",
    "        tag: subGroupName(),",
    "sub-formats.ts: سلکتورِ Sing-box")

# ۷) روت‌ها: PATCH اینباند + پیش‌فرضِ عنوانِ ساب ──────────────────────────────
sub("apps/server/src/routes.ts",
    "import { listInbounds, setInboundEnabled, getInbound } from \"./inbounds.js\";",
    "import { listInbounds, setInboundEnabled, getInbound, updateInbound } from \"./inbounds.js\";",
    "routes.ts: importِ updateInbound")
sub("apps/server/src/routes.ts",
    '''api.patch("/inbounds/:id", requirePermission("inbounds"), async (req: AuthedRequest, res) => {
  const id = Number(req.params.id);
  const body = z.object({ enabled: z.boolean() }).safeParse(req.body);
  if (!body.success || !getInbound(id)) {
    res.status(400).json({ error: "invalid" });
    return;
  }
  setInboundEnabled(id, body.data.enabled);
  logActivity(req.admin!.username, "inbound_toggle", `#${id} -> ${body.data.enabled}`);
  restartXray();
  res.json({ ok: true });
});''',
    '''api.patch("/inbounds/:id", requirePermission("inbounds"), async (req: AuthedRequest, res) => {
  const id = Number(req.params.id);
  // وصلهٔ ما: علاوه بر روشن/خاموش، ویرایشِ نامِ نمایشی/تگ/مسیر هم پذیرفته می‌شود
  const body = z
    .object({
      enabled: z.boolean().optional(),
      tag: z.string().optional(),
      label: z.string().optional(),
      path: z.string().optional(),
    })
    .safeParse(req.body);
  if (!body.success || !getInbound(id)) {
    res.status(400).json({ error: "invalid" });
    return;
  }
  if (body.data.tag !== undefined || body.data.label !== undefined || body.data.path !== undefined) {
    const result = updateInbound(id, {
      tag: body.data.tag,
      label: body.data.label,
      path: body.data.path,
    });
    if (!result.ok) {
      res.status(400).json({ error: result.error });
      return;
    }
    if (result.changed.length > 0) {
      logActivity(req.admin!.username, "inbound_edit", `#${id} ${result.changed.join(",")}`);
      restartXray();
    }
  }
  if (body.data.enabled !== undefined) {
    setInboundEnabled(id, body.data.enabled);
    logActivity(req.admin!.username, "inbound_toggle", `#${id} -> ${body.data.enabled}`);
    restartXray();
  }
  res.json({ ok: true, inbound: getInbound(id) });
});''',
    "routes.ts: PATCH اینباند")
sub("apps/server/src/routes.ts",
    "    subTitle: getSetting(\"sub_title\") || \"SideRail\",",
    "    subTitle: getSetting(\"sub_title\") || \"\",",
    "routes.ts: پیش‌فرضِ عنوانِ ساب")

# ۸) وب: نوع + کلاینتِ API + صفحهٔ اینباندها + ترجمه‌ها ──────────────────────
sub("apps/web/src/lib/types.ts",
    "export interface Inbound {\n  id: number;\n  tag: string;",
    "export interface Inbound {\n  id: number;\n  tag: string;\n  label: string;",
    "web/types.ts: label")
sub("apps/web/src/lib/api.ts",
    "  toggleInbound: (id: number, enabled: boolean) =>",
    "  updateInbound: (id: number, patch: Partial<{ enabled: boolean; tag: string; label: string; path: string }>) =>\n"
    "    request<{ ok: boolean; inbound: import(\"./types\").Inbound }>(`/api/inbounds/${id}`, {\n"
    "      method: \"PATCH\",\n"
    "      body: JSON.stringify(patch),\n"
    "    }),\n"
    "  toggleInbound: (id: number, enabled: boolean) =>",
    "web/api.ts: updateInbound")

I18N = {
    "en": '  inboundLabel: "Config name",\n  inboundTag: "Inbound tag",\n  inboundEditTitle: "Edit inbound",\n  inboundEditHint: "The config name shows up in the client. Path is what the tunnel listens on.",\n  inboundSaved: "Inbound saved",\n',
    "ru": '  inboundLabel: "Имя конфига",\n  inboundTag: "Тег входа",\n  inboundEditTitle: "Изменить входящий",\n  inboundEditHint: "Имя конфига отображается в клиенте. Путь — адрес туннеля.",\n  inboundSaved: "Входящий сохранён",\n',
    "zh": '  inboundLabel: "配置名称",\n  inboundTag: "入站标签",\n  inboundEditTitle: "编辑入站",\n  inboundEditHint: "配置名称会显示在客户端中。路径是隧道监听的地址。",\n  inboundSaved: "入站已保存",\n',
}
txt = read("apps/web/src/lib/i18n.tsx")
for lang, block in I18N.items():
    marker = {"en": '  inboundUpdated: "Inbound updated",\n',
              "ru": '  inboundUpdated: "Входящий обновлён",\n',
              "zh": '  inboundUpdated: "入站已更新",\n'}[lang]
    if marker not in txt:
        print(f"❌ i18n ({lang}): لنگر پیدا نشد"); sys.exit(1)
    txt = txt.replace(marker, marker + block, 1)
if not CHECK:
    write("apps/web/src/lib/i18n.tsx", txt)
done.append("web/i18n.tsx: کلیدهای تازه")

print("✅ وصله‌ها اعمال شد:" if not CHECK else "✅ بررسیِ لنگرها (بدونِ تغییر):")
for d in done:
    print("   •", d)
for s in skipped:
    print("   ⏭️ (نبود)", s)
