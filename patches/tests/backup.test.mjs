// آزمونِ محلیِ منطقِ بکاپ/ری‌استور روی دیتابیسِ قرنطینه (بدونِ تماس با پنلِ واقعی)
process.env.SIDERAIL_DATA_DIR = "/tmp/sr_bt/data";
const { mkdirSync, rmSync } = await import("node:fs");
rmSync("/tmp/sr_bt/data", { recursive: true, force: true });
mkdirSync("/tmp/sr_bt/data", { recursive: true });
const { db, migrate } = await import("/home/user/siderail-panel/apps/server/dist/db.js");
migrate();
const { importData, exportData } = await import("/home/user/siderail-panel/apps/server/dist/backup.js");
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
t("تعدادِ مسیرِ تازه‌شده = ۰ در حالتِ معمولی", r.freshPaths === 0);

// ② ری‌استور روی «پنلِ تازه»: پیشوند بماند، دمِ رندوم تازه شود
r = importData(backup, { freshPaths: true });
rows = db.prepare("SELECT id, tag, label, path FROM inbounds ORDER BY id").all();
t("پیشوندِ اول حفظ می‌شود (wpnfa)", rows[0].path.startsWith("/wpnfa/"), rows[0].path);
t("دمِ رندوم تازه است (≠ قبلی)", rows[0].path !== "/wpnfa/ws-XtN9GOHe", rows[0].path);
t("شکلِ مسیر مثلِ قبل: /wpnfa/ws-XXXXXXXX", /^\/wpnfa\/ws-[A-Za-z0-9_-]{8}$/.test(rows[0].path), rows[0].path);
t("نام‌ها در حالتِ تازه هم می‌مانند", rows[1].label === "خط دوم");
t("مسیرِ تک‌بخشی دست‌نخورده می‌ماند", rows[2].path === "/single", rows[2].path);
t("شمارنده درست است (۲ مسیرِ تازه از ۳)", r.freshPaths === 2, String(r.freshPaths));

// ③ خروجیِ بکاپ شاملِ نام است
const out = exportData();
t("خروجیِ بکاپ فیلدِ label را دارد", out.inbounds.every(x => "label" in x));

console.log("\n" + (fail === 0 ? `✅ همهٔ ${pass} آزمون سبز` : `❌ ${fail} ناموفق از ${pass + fail}`));
process.exit(fail ? 1 : 0);
