# ─────────────────────────────────────────────────────────────────────────────
#  sections_backup_light.py — بخشِ ۲۲: 💾 «بکاپِ سبک» = فقط تنظیمات
#
#  خواستهٔ کارفرما (۲۰۲۶-۰۹-۲۹):
#    ① «کاربرها تو بکاپ میان؛ می‌خواهم بکاپ فقط تنظیمات باشد، نه لیستِ کلاینت‌ها»
#    ② «قرار بود در بکاپ مسیر فقط wpnfa بماند، ولی کلِ مسیر را گرفته بود»
#
#  چه می‌کند:
#    • خروجیِ پیش‌فرضِ `/api/backup/export` = فقط `inbounds` + `settings`
#      (+ `version`/`exported_at`) ⇒ نه `users`، نه `user_inbounds`، نه `admins`.
#      بکاپِ کاملِ قبلی با `?full=1` (برای مهاجرتِ کاربران) در دسترس می‌ماند.
#    • مسیرِ هر اینباند در فایل فقط «بخشِ اول» ذخیره می‌شود:
#        `/wpnfa/ws-YWZ5weA_` ⇒ `/wpnfa`        `/SideRail/xhttp-4Hvmey_O` ⇒ `/SideRail`
#      چرا: مسیرِ کامل = کلیدِ زندهٔ تونلِ کاربران؛ نباید داخلِ فایلی بیفتد که
#      جابه‌جا/فوروارد می‌شود.
#    • ری‌استور: مسیرِ یک‌بخشی **خودکار** دمِ رندومِ تازه می‌گیرد
#      (کدِ سمتِ ری‌استور در «۱۳» است — همان‌جا که مسیرهای تازه از f80ی قبلی می‌آمد)
#      (`/wpnfa` ⇒ `/wpnfa/ws-<۸ رندوم>`) ⇒ پنلِ تازه مسیرِ تکراری با پنلِ قدیم ندارد.
#    • اگر فایل کاربران نداشت (بکاپِ سبک)، ری‌استور **لیستِ کاربرانِ فعلی را پاک
#      نمی‌کند** و پیوندِ کاربر↔اینباند (که با حذفِ اینباند آبشاری پاک می‌شود) برمی‌گردد.
#    • بکاپِ روزانهٔ تلگرام (`bot.ts`) هم از همین تابع می‌آید ⇒ حالا سبک است.
# ─────────────────────────────────────────────────────────────────────────────
from __future__ import annotations  # noqa: F407  (اجرای داخلِ panel-patch.py)

# ۲۲-۱) کمکی: فقط بخشِ اولِ مسیر ────────────────────────────────────────────────
sub("apps/server/src/backup.ts",
    'import { nanoid } from "nanoid";\nimport type { Inbound, UserRecord } from "./types.js";',
    'import { nanoid } from "nanoid";\nimport type { Inbound, UserRecord } from "./types.js";\n\n'
    '/** 🧩 (وصلهٔ ما) فقط «بخشِ اول» مسیر را نگه می‌دارد: ‎/wpnfa/ws-x‎ ⇒ ‎/wpnfa‎\n'
    ' *  چرا: مسیرِ کامل، کلیدِ زندهٔ تونلِ کاربران است و نباید در فایلِ بکاپ بیفتد.\n'
    ' *  دمِ رندوم هنگامِ ری‌استور تازه ساخته می‌شود. مسیرِ خالی دست‌نخورده می‌ماند. */\n'
    'export function firstPathSegment(path: unknown): string {\n'
    '  const seg = String(path || "").split("/").filter(Boolean);\n'
    '  return seg.length ? "/" + seg[0] : String(path || "");\n'
    '}\n',
    "backup.ts: firstPathSegment")

# ۲۲-۲) exportData ⇒ سبک (پیش‌فرض) + مسیرِ یک‌بخشی ─────────────────────────────
sub("apps/server/src/backup.ts",
    'export function exportData(): BackupPayload {\n'
    '  const users = db.prepare("SELECT * FROM users").all() as unknown as UserRecord[];\n'
    '  const inbounds = db.prepare("SELECT * FROM inbounds").all() as unknown as Inbound[];',
    '/** 🧩 (وصلهٔ ما) بکاپِ سبک = «فقط تنظیمات».\n'
    ' *  • `settingsOnly !== false` (پیش‌فرض): لیستِ مشتریان (`users`/`user_inbounds`)\n'
    ' *    و `admins` در فایل نمی‌آید ⇒ بکاپِ قابلِ جابه‌جایی.\n'
    ' *  • مسیرِ اینباندها فقط بخشِ اولشان ذخیره می‌شود (‎/wpnfa‎).\n'
    ' *  • برای بکاپِ کاملِ قبلی: `exportData({ settingsOnly: false })` یا `?full=1`. */\n'
    'export function exportData(options: { settingsOnly?: boolean } = {}): BackupPayload {\n'
    '  const settingsOnly = options.settingsOnly !== false;\n'
    '  const users = settingsOnly\n'
    '    ? []\n'
    '    : (db.prepare("SELECT * FROM users").all() as unknown as UserRecord[]);\n'
    '  const inbounds = (db.prepare("SELECT * FROM inbounds").all() as unknown as Inbound[]).map(\n'
    '    (ib) => ({ ...ib, path: firstPathSegment(ib.path) }),\n'
    '  );',
    "backup.ts: exportData سبک + مسیرِ کوتاه")

sub("apps/server/src/backup.ts",
    '  const links = db.prepare("SELECT user_id, inbound_id FROM user_inbounds").all() as unknown as {\n'
    '    user_id: number;\n'
    '    inbound_id: number;\n'
    '  }[];\n'
    '  const admins = db.prepare("SELECT * FROM admins").all() as unknown as AdminBackup[];',
    '  const links = settingsOnly\n'
    '    ? []\n'
    '    : (db.prepare("SELECT user_id, inbound_id FROM user_inbounds").all() as unknown as {\n'
    '        user_id: number;\n'
    '        inbound_id: number;\n'
    '      }[]);\n'
    '  const admins = settingsOnly\n'
    '    ? []\n'
    '    : (db.prepare("SELECT * FROM admins").all() as unknown as AdminBackup[]);',
    "backup.ts: بدونِ user_inbounds/admins در بکاپِ سبک")

sub("apps/server/src/backup.ts",
    '    for (const l of payload.user_inbounds) insLink.run(l.user_id, l.inbound_id);',
    '    for (const l of payload.user_inbounds) insLink.run(l.user_id, l.inbound_id);\n'
    '    // 🧩 (وصلهٔ ما) بکاپِ سبک: کاربرانِ فعلی با همین شناسه‌های اینباند وصل می‌مانند\n'
    '    if (!withUsers) for (const l of keepLinks) insLink.run(l.user_id, l.inbound_id);',
    "backup.ts: بازگرداندنِ پیوندِ کاربران")

# ۲۲-۵) مسیرِ HTTP: پیش‌فرض = سبک، `?full=1` = کامل ───────────────────────────
sub("apps/server/src/routes.ts",
    'api.get("/backup/export", requirePermission("dashboard"), (req: AuthedRequest, res) => {\n'
    '  logActivity(req.admin!.username, "backup_export", "");\n'
    '  res.setHeader("Content-Type", "application/json");\n'
    '  res.setHeader("Content-Disposition", `attachment; filename="siderail-backup-${Date.now()}.json"`);\n'
    '  res.send(JSON.stringify(exportData(), null, 2));\n'
    '});',
    'api.get("/backup/export", requirePermission("dashboard"), (req: AuthedRequest, res) => {\n'
    '  // 🧩 (وصلهٔ ما) پیش‌فرض = «بکاپِ سبک»: فقط تنظیمات/اینباندها، بدونِ لیستِ\n'
    '  //    مشتریان و با مسیرهای کوتاه (‎/wpnfa‎). `?full=1` = بکاپِ کاملِ قبلی.\n'
    '  const full = String(req.query.full || "") === "1";\n'
    '  logActivity(req.admin!.username, "backup_export", full ? "full" : "settings-only");\n'
    '  res.setHeader("Content-Type", "application/json");\n'
    '  res.setHeader(\n'
    '    "Content-Disposition",\n'
    '    `attachment; filename="siderail-${full ? "backup" : "settings"}-${Date.now()}.json"`,\n'
    '  );\n'
    '  res.send(JSON.stringify(exportData({ settingsOnly: !full }), null, 2));\n'
    '});',
    "routes.ts: export سبک/کامل")

# ۲۲-۶) وب: آدرسِ بکاپِ کامل + دکمهٔ کوچک ──────────────────────────────────────
sub("apps/web/src/lib/api.ts",
    'export function exportBackupUrl(): string {\n  return "/api/backup/export";\n}',
    '/** 🧩 (وصلهٔ ما) پیش‌فرض = بکاپِ سبک (تنظیمات + اینباندها، بدونِ مشتریان).\n'
    ' *  `full=true` ⇒ همان بکاپِ کاملِ قبلی (شاملِ کاربران و ادمین‌ها). */\n'
    'export function exportBackupUrl(full?: boolean): string {\n'
    '  return "/api/backup/export" + (full ? "?full=1" : "");\n'
    '}',
    "web/api.ts: exportBackupUrl(full)")

sub("apps/web/src/pages/dashboard.tsx",
    '  const onExport = () => {\n'
    '    window.open(exportBackupUrl(), "_blank");\n'
    '    toast.push("success", t("backupExportStarted"));\n'
    '  };',
    '  const onExport = () => {\n'
    '    window.open(exportBackupUrl(), "_blank");\n'
    '    toast.push("success", t("backupExportStarted"));\n'
    '  };\n\n'
    '  // 🧩 (وصلهٔ ما) بکاپِ کامل (شاملِ لیستِ مشتریان) برای مهاجرتِ کاربران\n'
    '  const onExportFull = () => {\n'
    '    window.open(exportBackupUrl(true), "_blank");\n'
    '    toast.push("success", t("backupExportStarted"));\n'
    '  };',
    "web/dashboard.tsx: onExportFull")

sub("apps/web/src/pages/dashboard.tsx",
    '              <div>\n'
    '                <div className="font-heading">{t("exportBackup")}</div>\n'
    '                <div className="text-xs text-text/60">{t("exportBackupDesc")}</div>\n'
    '              </div>',
    '              <div>\n'
    '                <div className="font-heading">{t("exportBackup")}</div>\n'
    '                <div className="text-xs text-text/60">{t("exportBackupDesc")}</div>\n'
    '                <span\n'
    '                  onClick={(ev) => {\n'
    '                    ev.stopPropagation();\n'
    '                    onExportFull();\n'
    '                  }}\n'
    '                  className="mt-1 inline-block text-[11px] underline decoration-dotted opacity-70 hover:opacity-100"\n'
    '                >\n'
    '                  {t("exportFullBackup")}\n'
    '                </span>\n'
    '              </div>',
    "web/dashboard.tsx: لینکِ بکاپِ کامل")

# ۲۲-۷) i18n: توضیحِ تازه + کلیدِ بکاپِ کامل ───────────────────────────────────
I18N3 = [
    ("en", "Settings only — inbounds & preferences (no client list). Paths are shortened.",
           "Full backup (incl. clients)",
           "Importing replaces inbounds & settings. The client list stays, unless the file contains clients."),
    ("ru", "Только настройки — входящие и параметры (без списка клиентов). Пути сокращены.",
           "Полная копия (с клиентами)", None),
    ("zh", "仅设置——入站与偏好（不含客户端列表）。路径已缩短。",
           "完整备份（含客户端）",
           "导入将替换入站和设置。除非文件包含客户端，否则客户端列表保持不变。"),
]
_txt3 = read("apps/web/src/lib/i18n.tsx")

# ۲۲-۷-الف) توضیحِ کارتِ بکاپ + کلیدِ «بکاپِ کامل» (سه زبان، به ترتیبِ فایل) ──
if "exportFullBackup" not in _txt3:
    _it3 = iter(I18N3)

    def _rep3(m):
        _lang, _desc, _full, _warn = next(_it3)
        _pad = m.group("pad")
        return (
            _pad + "exportBackupDesc: " + json.dumps(_desc, ensure_ascii=False) + ",\n"
            + _pad + "exportFullBackup: " + json.dumps(_full, ensure_ascii=False) + ","
        )

    _txt3, _n = re.subn(r'^(?P<pad> *)(?:exportBackupDesc: )"[^"\n]*",$', _rep3, _txt3, flags=re.M)
    if _n != len(I18N3):
        print(f"❌ i18n3: توضیحِ بکاپ در {_n} زبان عوض شد (انتظار {len(I18N3)})")
        sys.exit(1)

# ۲۲-۷-ب) هشدارِ ری‌استور: مشتریان پاک نمی‌شوند (en + zh تک‌خطی، ru دو‌خطی) ────
_warns = [(l, w) for (l, _d, _f, w) in I18N3 if w]
_wi = iter(_warns)


def _repw(m):
    _lang, _warn = next(_wi)
    _new_line = "  importWarning: " + json.dumps(_warn, ensure_ascii=False) + ","
    return m.group(0) if m.group(0) == _new_line else _new_line


_txt3, _n = re.subn(r'^  importWarning: "[^"\n]*",$', _repw, _txt3, flags=re.M)
if _n != len(_warns):
    print(f"❌ i18n3: importWarning در {_n} زبان (انتظار {len(_warns)})")
    sys.exit(1)
_ru_old = re.compile(r'^  importWarning:\n    "[^"\n]*",$', re.M)
if _ru_old.search(_txt3):
    _txt3 = _ru_old.sub(
        '  importWarning:\n    "Импорт заменяет входящие и настройки. Список клиентов сохраняется.",',
        _txt3, count=1)
if not CHECK:
    write("apps/web/src/lib/i18n.tsx", _txt3)
done.append("web/i18n.tsx: توضیحِ بکاپِ سبک + کلیدِ بکاپِ کامل + هشدارِ ری‌استور")
