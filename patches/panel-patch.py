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
import argparse, io, json, os, re, sys

ROOT = os.environ.get("SIDERAIL_ROOT", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
done, skipped = [], []

def read(rel):
    return io.open(os.path.join(ROOT, rel), encoding="utf-8").read()

def write(rel, txt):
    io.open(os.path.join(ROOT, rel), "w", encoding="utf-8").write(txt)

def sub(rel, old, new, label, count=1, required=True):
    """جای‌گزینیِ لنگر‌محور. اگر متنِ تازه از قبل باشد، «انجام‌شده» شمرده می‌شود
    (اجرای دوبارهٔ وصله‌گر روی سورسِ وصله‌خورده، وصله‌ها را دوباره اعمال نمی‌کند)."""
    txt = read(rel)
    if new is not None and txt.count(new) >= count:
        done.append(label + " (از قبل)")
        return
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
# 🔁 اگر توابعِ ما از قبل هستند (سورسِ وصله‌خورده)، دوباره اضافه نکن
if "export function updateInbound(" in read("apps/server/src/inbounds.ts"):
    done.append("inbounds.ts: updateInbound + normalizeInboundPath (از قبل)")
else:
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
    "en": '  editShort: "Edit",\n  inboundPathWarn: "⚠️ Changing the path breaks the configs already given to users from this inbound. The tag and the display name are safe to change.",\n  inboundLabel: "Config name",\n  inboundTag: "Inbound tag",\n  inboundEditTitle: "Edit inbound",\n  inboundEditHint: "The config name shows up in the client. Path is what the tunnel listens on.",\n  inboundSaved: "Inbound saved",\n',
    "ru": '  editShort: "Изменить",\n  inboundPathWarn: "⚠️ Смена пути сломает уже выданные конфиги этого входа. Тег и отображаемое имя менять безопасно.",\n  inboundLabel: "Имя конфига",\n  inboundTag: "Тег входа",\n  inboundEditTitle: "Изменить входящий",\n  inboundEditHint: "Имя конфига отображается в клиенте. Путь — адрес туннеля.",\n  inboundSaved: "Входящий сохранён",\n',
    "zh": '  editShort: "编辑",\n  inboundPathWarn: "⚠️ 更改路径会使该入站已发给用户的配置失效。标签和显示名称可以安全更改。",\n  inboundLabel: "配置名称",\n  inboundTag: "入站标签",\n  inboundEditTitle: "编辑入站",\n  inboundEditHint: "配置名称会显示在客户端中。路径是隧道监听的地址。",\n  inboundSaved: "入站已保存",\n',
}
txt = read("apps/web/src/lib/i18n.tsx")
# پاک‌سازیِ نسخهٔ قبلیِ همین کلیدها (اجرای دوباره‌ی وصله‌گر نباید کلید تکراری بسازد)
_our_keys = sorted({m.group(1) for blk in I18N.values() for m in re.finditer(r"(\w+):", blk)})
for _k in _our_keys:
    txt = re.sub(r"^\s*" + re.escape(_k) + r":.*\n", "", txt, flags=re.M)
for lang, block in I18N.items():
    marker = {"en": '  inboundUpdated: "Inbound updated",\n',
              "ru": '  inboundUpdated: "Входящий обновлён",\n',
              "zh": '  inboundUpdated: "入站已更新",\n'}[lang]
    if block in txt:            # از قبل اعمال شده
        continue
    if marker not in txt:
        print(f"❌ i18n ({lang}): لنگر پیدا نشد"); sys.exit(1)
    txt = txt.replace(marker, marker + block, 1)
if not CHECK:
    write("apps/web/src/lib/i18n.tsx", txt)
done.append("web/i18n.tsx: کلیدهای تازه")

# ۹) انقضای مطلق (expireAt) + حجمِ اعشاری — برای انتقالِ دقیقِ «ساعت/مگابایتِ باقی‌مانده»
#    در دکمهٔ «ریستِ کانفیگ» ربات. `expireDays` نسبی بود و ۲۱ ساعت را ۱ روز می‌کرد.
sub("apps/server/src/users.ts",
    "  expireDays?: number;\n  subExpireDays?: number;",
    "  expireDays?: number;\n  /** انقضای مطلق (epoch ms) — بر expireDays اولویت دارد */\n  expireAt?: number;\n  subExpireDays?: number;",
    "users.ts: expireAt در CreateUserInput")
sub("apps/server/src/users.ts",
    "      gb(input.dataLimit || 0),\n      input.ipLimit || 0,\n      expireFromDays(input.expireDays),",
    "      gb(input.dataLimit || 0),\n      input.ipLimit || 0,\n      (input.expireAt != null ? input.expireAt : expireFromDays(input.expireDays)),",
    "users.ts: expireAt در createUser")
sub("apps/server/src/users.ts",
    '  if (input.expireDays !== undefined) set("expire_at", expireFromDays(input.expireDays));',
    '  if (input.expireDays !== undefined) set("expire_at", expireFromDays(input.expireDays));\n'
    '  if (input.expireAt !== undefined) set("expire_at", input.expireAt || null);',
    "users.ts: expireAt در updateUser")
sub("apps/server/src/routes.ts",
    "  expireDays: z.number().min(0).optional(),",
    "  expireDays: z.number().min(0).optional(),\n  expireAt: z.number().int().min(0).optional(),",
    "routes.ts: expireAt در userSchema")

# ۱۰) همهٔ IPها یک‌جا — برای شمارشِ «چند دستگاه به این کانفیگ وصل است»
#     (ربات با یک درخواست، تعداد دستگاهِ همهٔ کاربران را می‌گیرد)
sub("apps/server/src/xray.ts",
    "export function getClientIps(userId: number): { ip: string; last_seen: number }[] {",
    "/** 🧩 وصله: IPهای همهٔ کاربران یک‌جا (شمارشِ دستگاه‌ها در ربات) */\n"
    "export function getAllClientIps(): { user_id: number; clientEmail: string; ip: string; last_seen: number }[] {\n"
    "  return db\n"
    "    .prepare(\n"
    '      "SELECT c.user_id AS user_id, u.email AS clientEmail, c.ip AS ip, c.last_seen AS last_seen " +\n'
    '        "FROM client_ips c JOIN users u ON u.id = c.user_id ORDER BY c.last_seen DESC",\n'
    "    )\n"
    "    .all() as { user_id: number; clientEmail: string; ip: string; last_seen: number }[];\n"
    "}\n\n"
    "export function getClientIps(userId: number): { ip: string; last_seen: number }[] {",
    "xray.ts: getAllClientIps")
sub("apps/server/src/routes.ts",
    'import { getClientIps, restartXray, getServerTraffic, getInboundTraffic } from "./xray.js";',
    'import { getClientIps, getAllClientIps, restartXray, getServerTraffic, getInboundTraffic } from "./xray.js";',
    "routes.ts: importِ getAllClientIps")
sub("apps/server/src/routes.ts",
    'api.get("/users/:id/ips", requirePermission("users"), (req: AuthedRequest, res) => {',
    '/** 🧩 وصله: همهٔ IPها یک‌جا — ربات با یک درخواست دستگاه‌های همه را می‌شمارد */\n'
    'api.get("/ips", requirePermission("users"), (_req: AuthedRequest, res) => {\n'
    "  res.json({ ips: getAllClientIps() });\n"
    "});\n\n"
    'api.get("/users/:id/ips", requirePermission("users"), (req: AuthedRequest, res) => {',
    "routes.ts: GET /ips")

# ۱۱) صفحهٔ اینباندها (کلِ فایل): دکمهٔ «✏️ ویرایش» با برچسب + دیالوگِ نام/تگ/مسیر
#     + هشدارِ تغییرِ مسیر. فایلِ کامل در patches/files/inbounds.tsx نگه داشته می‌شود تا
#     روی هر نسخهٔ تازهٔ upstream هم قابلِ بازتولید باشد.
# ۱۲) 🏷 نامِ اینباند با فارسی/ایموجی/| هم پذیرفته شود ─────────────────────────
#     چرا: کارفرما می‌خواست اینباند را «2 | هلند 🇳🇱» بنامد؛ فیلدِ تگ فقط
#     [A-Za-z0-9 _.-] می‌پذیرفت. تگ داخلِ JSON کانفیگ می‌رود و روتینگ به آن با
#     شناسهٔ (id) اینباند وصل است ⇒ تغییرِ نام بی‌خطر است. فقط کاراکترهایی که
#     می‌توانند ساختار را بشکنند (کنترل/کوتیشن/بک‌اسلش/براکت) ممنوع می‌مانند.
sub("apps/server/src/inbounds.ts",
    '    if (!/^[A-Za-z0-9 _.-]{1,32}$/.test(tag))\n'
    '      return { ok: false, error: "tag may only contain letters, digits, space, _ . -  (1..32)" };',
    '    // 🏷 (وصلهٔ ما) نامِ تگ آزاد است: فارسی/ایموجی/فاصله/| — فقط کاراکترهای\n'
    '    //    خطرناک ممنوع؛ چون تگ داخلِ JSON کانفیگ می‌رود و روتینگ با id وصل است.\n'
    '    if (tag.length < 1 || tag.length > 40 || /[\\u0000-\\u001f\\u007f"\'`\\\\<>]/.test(tag))\n'
    '      return { ok: false, error: "tag: 1..40 chars — no control/quotes/brackets" };',
    "inbounds.ts: تگِ آزاد (فارسی/ایموجی)")

# ۱۳) 💾 بکاپ: نامِ اینباند هم برگردد + گزینهٔ «رندومِ مسیرها تازه شود» ─────────
#     باگ: خروجیِ بکاپ نام (label) را داشت (SELECT *)، ولی import آن را
#     درج نمی‌کرد ⇒ بعد از ری‌استور، نامِ اینباندها می‌پرید.
#     خواستهٔ کارفرما: در ری‌استور روی پنلِ تازه، فقط «بخشِ اولِ مسیر» (مثل wpnfa)
#     از بکاپ بماند و بقیه (transport-rand8) رندومِ تازه بگیرد.
sub("apps/server/src/backup.ts",
    "  const tx = () => {\n    db.exec(\"DELETE FROM user_inbounds; DELETE FROM users; DELETE FROM inbounds;\");",
    "  // 🧩 (وصلهٔ ما) شمارندهٔ مسیرهای تازه‌ساخته‌شده — بیرونِ تراکنش تعریف می‌شود\n  let freshPaths = 0;\n  const tx = () => {\n    db.exec(\"DELETE FROM user_inbounds; DELETE FROM users; DELETE FROM inbounds;\");",
    "backup.ts: شمارندهٔ freshPaths")
sub("apps/server/src/backup.ts",
    "export function importData(payload: BackupPayload): { users: number; inbounds: number } {",
    "export function importData(\n"
    "  payload: BackupPayload,\n"
    "  options: { freshPaths?: boolean } = {},\n"
    "): { users: number; inbounds: number; freshPaths: number } {",
    "backup.ts: امضای importData")
sub("apps/server/src/backup.ts",
    '      `INSERT INTO inbounds (id, tag, protocol, transport, port, path, host, enabled, created_at)\n'
    '       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)`,',
    '      `INSERT INTO inbounds (id, tag, label, protocol, transport, port, path, host, enabled, created_at)\n'
    '       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,',
    "backup.ts: label در INSERT")
sub("apps/server/src/backup.ts",
    "    for (const ib of payload.inbounds) {\n      insInbound.run(\n        ib.id,\n        ib.tag,\n        ib.protocol,\n        ib.transport,\n        ib.port,\n        ib.path,\n        ib.host,\n        ib.enabled,\n        ib.created_at,\n      );\n    }",
    "    for (const ib of payload.inbounds) {\n      // 🧩 (وصلهٔ ما) گزینهٔ «مسیرِ تازه»: پیشوندِ اول از بکاپ می‌ماند (مثل wpnfa)\n      //     و دمِ رندوم دوباره ساخته می‌شود ⇒ پنلِ تازه تصادمِ مسیر با پنلِ قدیم ندارد.\n      let path = ib.path;\n      if (options.freshPaths) {\n        const seg = String(ib.path || \"\").split(\"/\").filter(Boolean);\n        if (seg.length >= 2) {\n          path = \"/\" + seg[0] + \"/\" + (ib.transport || \"ws\") + \"-\" + nanoid(8);\n          freshPaths++;\n        }\n      }\n      insInbound.run(\n        ib.id,\n        ib.tag,\n        ib.label ?? \"\", // 🧩 نامِ اینباند (قبلاً جا می‌افتاد)\n        ib.protocol,\n        ib.transport,\n        ib.port,\n        path,\n        ib.host,\n        ib.enabled,\n        ib.created_at,\n      );\n    }",
    "backup.ts: label + مسیرِ تازه")
sub("apps/server/src/backup.ts",
    "  return { users: payload.users.length, inbounds: payload.inbounds.length };",
    "  return { users: payload.users.length, inbounds: payload.inbounds.length, freshPaths };",
    "backup.ts: خروجیِ import")
sub("apps/server/src/backup.ts",
    "import { nanoid } from \"nanoid\";",
    "import { nanoid } from \"nanoid\";",
    "backup.ts: nanoid (اگر بود)", required=False)
sub("apps/server/src/backup.ts",
    'import { db } from "./db.js";',
    'import { db } from "./db.js";\nimport { nanoid } from "nanoid";',
    "backup.ts: import nanoid", required=False)

# ۱۴) مسیر HTTP: پرچمِ freshPaths برای ری‌استور
sub("apps/server/src/routes.ts",
    "    const result = importData(req.body);",
    "    // 🧩 (وصلهٔ ما) ?freshPaths=1 ⇒ فقط پیشوندِ مسیر از بکاپ بماند و دمِ رندوم تازه شود\n"
    "    const result = importData(req.body, { freshPaths: String(req.query.freshPaths || \"\") === \"1\" });",
    "routes.ts: freshPaths در import")

# ۱۵) UI: چک‌باکسِ «مسیرهای تازه» + عبورِ پرچم
sub("apps/web/src/lib/api.ts",
    '  importBackup: (data: unknown) =>\n'
    '    request("/api/backup/import", { method: "POST", body: JSON.stringify(data) }),',
    '  // 🧩 (وصلهٔ ما) freshPaths ⇒ پیشوندِ مسیر بماند، دمِ رندوم تازه شود\n'
    '  importBackup: (data: unknown, freshPaths?: boolean) =>\n'
    '    request(`/api/backup/import${freshPaths ? "?freshPaths=1" : ""}`, {\n'
    '      method: "POST",\n'
    '      body: JSON.stringify(data),\n'
    '    }),',
    "web/api.ts: importBackup(freshPaths)")
sub("apps/web/src/pages/dashboard.tsx",
    "  const [importing, setImporting] = React.useState(false);",
    "  const [importing, setImporting] = React.useState(false);\n"
    "  // 🧩 (وصلهٔ ما) مسیرهای تازه در ری‌استور (پیش‌فرض: خاموش = امن)\n"
    "  const [freshPaths, setFreshPaths] = React.useState(false);",
    "web/dashboard.tsx: state")
sub("apps/web/src/pages/dashboard.tsx",
    "      await api.importBackup(json);",
    "      await api.importBackup(json, freshPaths);",
    "web/dashboard.tsx: عبورِ freshPaths")
sub("apps/web/src/pages/dashboard.tsx",
    '          <p className="mt-3 text-xs font-base text-text/50">{t("importWarning")}</p>',
    '          <label className="mt-4 flex cursor-pointer items-start gap-3 rounded-base border-2 border-border/60 p-3">\n'
    '            <input\n'
    '              type="checkbox"\n'
    '              className="mt-0.5 h-4 w-4"\n'
    '              checked={freshPaths}\n'
    '              onChange={(e) => setFreshPaths(e.target.checked)}\n'
    '            />\n'
    '            <span>\n'
    '              <span className="block font-heading text-sm">{t("importFreshPaths")}</span>\n'
    '              <span className="block text-xs font-base text-text/60">{t("importFreshPathsHint")}</span>\n'
    '            </span>\n'
    '          </label>\n'
    '          <p className="mt-3 text-xs font-base text-text/50">{t("importWarning")}</p>',
    "web/dashboard.tsx: چک‌باکس")

# ۱۶) i18n چک‌باکس
I18N2 = {
    "en": '  importFreshPaths: "Refresh config paths (keep the first part, like wpnfa)",\n  importFreshPathsHint: "Use this when restoring into a NEW panel: the first path segment is kept from the backup and the random tail is regenerated.",\n',
    "ru": '  importFreshPaths: "Обновить пути конфигов (первая часть сохраняется, например wpnfa)",\n  importFreshPathsHint: "Для восстановления на НОВОЙ панели: первый сегмент пути берётся из бэкапа, случайная часть создаётся заново.",\n',
    "zh": '  importFreshPaths: "刷新配置路径（保留第一段，如 wpnfa）",\n  importFreshPathsHint: "在新面板恢复时使用：路径的第一段取自备份，随机后缀重新生成。",\n',
}
_txt = read("apps/web/src/lib/i18n.tsx")
_our2 = sorted({m.group(1) for blk in I18N2.values() for m in re.finditer(r"(\w+):", blk)})
for _k in _our2:
    _txt = re.sub(r"^\s*" + re.escape(_k) + r":.*\n", "", _txt, flags=re.M)
for lang, block in I18N2.items():
    marker = {"en": '  inboundUpdated: "Inbound updated",\n',
              "ru": '  inboundUpdated: "Входящий обновлён",\n',
              "zh": '  inboundUpdated: "入站已更新",\n'}[lang]
    if block in _txt:
        continue
    if marker not in _txt:
        print(f"❌ i18n2 ({lang}): لنگر پیدا نشد"); sys.exit(1)
    _txt = _txt.replace(marker, marker + block, 1)
if not CHECK:
    write("apps/web/src/lib/i18n.tsx", _txt)
done.append("web/i18n.tsx: کلیدهای ری‌استورِ مسیر")

def copy_file(rel_src, rel_dst, label):
    # فایلِ منبع کنارِ خودِ این اسکریپت است (در حالتِ --check هم در دسترس باشد)
    src_p = os.path.join(os.path.dirname(os.path.abspath(__file__)), rel_src.replace("patches/", "", 1))
    dst_p = os.path.join(ROOT, rel_dst)
    if not os.path.exists(src_p):
        print(f"❌ {label}: فایلِ منبع پیدا نشد ({rel_src})"); sys.exit(1)
    new_txt = io.open(src_p, encoding="utf-8").read()
    old_txt = io.open(dst_p, encoding="utf-8").read() if os.path.exists(dst_p) else ""
    if old_txt == new_txt:
        done.append(label + " (از قبل)"); return
    if "InboundsPage" not in old_txt:
        print(f"❌ {label}: فایلِ مقصد شکلِ موردانتظار را ندارد"); sys.exit(1)
    if not CHECK:
        io.open(dst_p, "w", encoding="utf-8").write(new_txt)
    done.append(label)

copy_file("patches/files/inbounds.tsx", "apps/web/src/pages/inbounds.tsx",
          "web/inbounds.tsx: دکمهٔ ویرایش + هشدارِ مسیر")

# ── ۱۷–۲۱) 🔑 توکنِ دسترسیِ ربات (فایلِ جدا: patches/sections_bot_token.py) ──
_sect = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sections_bot_token.py")
if os.path.exists(_sect):
    exec(compile(io.open(_sect, encoding="utf-8").read(), "sections_bot_token.py", "exec"), globals())

print("✅ وصله‌ها اعمال شد:" if not CHECK else "✅ بررسیِ لنگرها (بدونِ تغییر):")
for d in done:
    print("   •", d)
for s in skipped:
    print("   ⏭️ (نبود)", s)
