// آزمونِ محلیِ منطقِ بکاپ/ری‌استور روی دیتابیسِ قرنطینه (بدونِ تماس با پنلِ واقعی)
process.env.SIDERAIL_DATA_DIR = "/tmp/sr_bt/data";
const { mkdirSync, rmSync } = await import("node:fs");
rmSync("/tmp/sr_bt/data", { recursive: true, force: true });
mkdirSync("/tmp/sr_bt/data", { recursive: true });
const { db, migrate } = await import("/home/user/siderail-panel/apps/server/dist/db.js");
migrate();
const { importData, exportData, firstPathSegment } = await import("/home/user/siderail-panel/apps/server/dist/backup.js");
let pass = 0, fail = 0;
const t = (n, ok, x) => { ok ? (pass++, console.log("  ✅ " + n)) : (fail++, console.log("  ❌ " + n + (x ? " → " + x : ""))); };

db.exec("DELETE FROM inbounds");
const mk = (id, tag, label, tr, path) => ({ id, tag, label, protocol: "vless", transport: tr, port: 20000 + id,
  path, host: "", enabled: 1, created_at: Date.now() });
const backup = { version: 2, users: [], user_inbounds: [], inbounds: [
  mk(1, "2", "2 | هلند 🇳🇱", "ws", "/wpnfa/ws-XtN9GOHe"),
  mk(2, "VLESS-XHTTP", "خط دوم", "xhttp", "/wpnfa/xhttp-jm7huwvB"),
  mk(3, "Trojan-WS", "", "ws", "/single"),
], admins: [] };

// ① ری‌استورِ معمولی: همه‌چیز عیناً (نام‌ها هم) باید برگردد
let r = importData(backup);
let rows = db.prepare("SELECT id, tag, label, path FROM inbounds ORDER BY id").all();
t("نام‌ها بعد از ری‌استور می‌مانند", rows[0].label === "2 | هلند 🇳🇱" && rows[1].label === "خط دوم", JSON.stringify(rows[0]));
t("تگِ فارسی/ایموجی هم ذخیره می‌شود", rows[0].tag === "2");
t("مسیرِ پیش‌فرض دست‌نخورده است", rows[0].path === "/wpnfa/ws-XtN9GOHe", rows[0].path);
// 🆕 بخشِ ۲۲: در حالتِ معمولی فقط مسیرِ تک‌بخشی دمِ رندوم می‌گیرد (مسیرِ دوبخشی دست‌نخورده است)
t("تعدادِ مسیرِ تازه‌شده = ۱ در حالتِ معمولی (فقط تک‌بخشی)", r.freshPaths === 1, String(r.freshPaths));
t("مسیرِ دوبخشیِ دیگر هم دست‌نخورده ماند", rows[1].path === "/wpnfa/xhttp-jm7huwvB", rows[1].path);

// ② ری‌استور روی «پنلِ تازه»: پیشوند بماند، دمِ رندوم تازه شود
r = importData(backup, { freshPaths: true });
rows = db.prepare("SELECT id, tag, label, path FROM inbounds ORDER BY id").all();
t("پیشوندِ اول حفظ می‌شود (wpnfa)", rows[0].path.startsWith("/wpnfa/"), rows[0].path);
t("دمِ رندوم تازه است (≠ قبلی)", rows[0].path !== "/wpnfa/ws-XtN9GOHe", rows[0].path);
t("شکلِ مسیر مثلِ قبل: /wpnfa/ws-XXXXXXXX", /^\/wpnfa\/ws-[A-Za-z0-9_-]{8}$/.test(rows[0].path), rows[0].path);
t("نام‌ها در حالتِ تازه هم می‌مانند", rows[1].label === "خط دوم");
// 🆕 بخشِ ۲۲: مسیرِ تک‌بخشی هم دمِ رندوم می‌گیرد (خروجیِ بکاپِ سبک این‌شکلی است)
t("مسیرِ تک‌بخشی هم دمِ رندوم می‌گیرد", /^\/single\/ws-[A-Za-z0-9_-]{8}$/.test(rows[2].path), rows[2].path);
t("شمارنده درست است (هر ۳ مسیر تازه شد)", r.freshPaths === 3, String(r.freshPaths));

// ③ 🆕 خروجیِ بکاپِ سبک: فقط تنظیمات (بدونِ مشتریان) و مسیرهای کوتاه
importData(backup);                                   // دوباره مسیرهای کامل
db.exec("DELETE FROM users; DELETE FROM user_inbounds;");
const addUser = db.prepare(
  `INSERT INTO users (id, email, uuid, password, sub_token, fingerprint, alpn, data_limit, ip_limit,
    expire_at, sub_expire_days, sub_first_seen, traffic_reset, telegram_id, comment, enabled, up, down,
    last_reset, online_at, created_by, created_at)
   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`);
addUser.run(7, "u7", "11111111-2222-3333-4444-555555555555", "pw", "subt", "chrome", "h2",
  0, 0, 0, 0, 0, "never", "", "", 1, 0, 0, 0, 0, null, 0);
db.prepare("INSERT INTO user_inbounds (user_id, inbound_id) VALUES (7, 1)").run();

const light = exportData();
t("بکاپِ پیش‌فرض لیستِ مشتریان را ندارد", Array.isArray(light.users) && light.users.length === 0);
t("بکاپِ پیش‌فرض پیوندِ کاربر↔اینباند را ندارد", Array.isArray(light.user_inbounds) && light.user_inbounds.length === 0);
t("بکاپِ پیش‌فرض ادمین‌ها را ندارد", Array.isArray(light.admins) && light.admins.length === 0);
t("بکاپِ پیش‌فرض تنظیمات و اینباندها را دارد", light.inbounds.length === 3 && Array.isArray(light.settings));
t("مسیر در بکاپ فقط بخشِ اول است", light.inbounds[0].path === "/wpnfa" && light.inbounds[2].path === "/single",
  light.inbounds.map((x) => x.path).join(" | "));
t("نامِ اینباند در بکاپ می‌ماند", light.inbounds[0].label === "2 | هلند 🇳🇱");
const full = exportData({ settingsOnly: false });
t("بکاپِ کامل کاربران را دارد", full.users.length === 1 && full.user_inbounds.length === 1);
t("بکاپِ کامل مسیرها را هم کوتاه می‌کند", full.inbounds[0].path === "/wpnfa", full.inbounds[0].path);
t("کمکیِ firstPathSegment درست کار می‌کند", firstPathSegment("/a/b/c") === "/a" && firstPathSegment("") === "");

// ④ 🆕 ری‌استورِ بکاپِ سبک: مشتریانِ فعلی پاک نمی‌شوند و پیوندها برمی‌گردند
const light2 = JSON.parse(JSON.stringify(light));
light2.inbounds[0].label = "نامِ تازه";
const before = db.prepare("SELECT path FROM inbounds WHERE id = 1").get().path;
const r2 = importData(light2);
t("ری‌استورِ سبک کاربران را نگه می‌دارد", db.prepare("SELECT COUNT(*) c FROM users").get().c === 1);
t("پیوندِ کاربر↔اینباند برمی‌گردد", db.prepare("SELECT COUNT(*) c FROM user_inbounds").get().c === 1);
t("نامِ تازهٔ اینباند اعمال شد", db.prepare("SELECT label FROM inbounds WHERE id = 1").get().label === "نامِ تازه");
const after = db.prepare("SELECT path FROM inbounds WHERE id = 1").get().path;
t("مسیرِ کوتاه در ری‌استور دمِ رندوم گرفت", /^\/wpnfa\/ws-[A-Za-z0-9_-]{8}$/.test(after) && after !== before, after);
t("خروجیِ ری‌استورِ سبک: صفر کاربر ولی ۳ مسیرِ تازه", r2.users === 0 && r2.freshPaths === 3, JSON.stringify(r2));

// ⑤ بکاپِ کامل هنوز کاربران را جای‌گزین می‌کند (رفتارِ قبلی)
const withUsers = { version: 2, users: [{ ...db.prepare("SELECT * FROM users WHERE id = 7").get(), id: 9, email: "u9" }],
  user_inbounds: [{ user_id: 9, inbound_id: 2 }],
  inbounds: [mk(1, "2", "x", "ws", "/wpnfa/ws-aaaaaaaa"), mk(2, "3", "y", "ws", "/wpnfa/ws-bbbbbbbb")], admins: [] };
const r3 = importData(withUsers, { freshPaths: true });
t("بکاپِ کامل کاربران را عوض می‌کند", db.prepare("SELECT email FROM users").get().email === "u9");
t("پیوندِ کاربرِ تازه ساخته شد", db.prepare("SELECT COUNT(*) c FROM user_inbounds").get().c === 1);
t("مسیرِ دوبخشی در بکاپِ کامل هم تازه شد", r3.freshPaths === 2, String(r3.freshPaths));

const out = exportData({ settingsOnly: false });
t("خروجیِ بکاپ فیلدِ label را دارد", out.inbounds.every(x => "label" in x));

console.log("\n" + (fail === 0 ? `✅ همهٔ ${pass} آزمون سبز` : `❌ ${fail} ناموفق از ${pass + fail}`));
process.exit(fail ? 1 : 0);
