// آزمونِ محلیِ «توکنِ دسترسیِ ربات» روی دیتابیسِ قرنطینه (بدونِ تماس با پنلِ واقعی)
process.env.SIDERAIL_DATA_DIR = "/tmp/sr_tok/data";
const { mkdirSync, rmSync } = await import("node:fs");
rmSync("/tmp/sr_tok/data", { recursive: true, force: true });
mkdirSync("/tmp/sr_tok/data", { recursive: true });
const { db, migrate } = await import("/home/user/siderail-panel/apps/server/dist/db.js");
migrate();
const {
  createApiToken,
  listApiTokens,
  verifyApiToken,
  revokeApiToken,
  deleteApiToken,
  panelHandshake,
  originFromHeaders,
  API_TOKEN_PREFIX,
} = await import("/home/user/siderail-panel/apps/server/dist/api-tokens.js");
let pass = 0, fail = 0;
const t = (n, ok, x) => { ok ? (pass++, console.log("  ✅ " + n)) : (fail++, console.log("  ❌ " + n + (x ? " → " + x : ""))); };

// ① جدول ساخته می‌شود
const tbl = db.prepare("SELECT name FROM sqlite_master WHERE type='table' AND name='api_tokens'").get();
t("جدولِ api_tokens ساخته می‌شود", !!tbl);

// ② ساختِ توکن: شکل و محتوا
const ORIGIN = "https://panel.example.com";
const made = createApiToken("telegram-bot", ORIGIN);
t("ساختِ توکن موفق است", made.ok === true && !!made.token);
const tok = made.token || "";
const parts = tok.split(".");
t("شکلِ توکن srb1.<payload>.<id>.<secret>", parts.length === 4 && parts[0] === "srb1", tok.slice(0, 24) + "…");
t("پیشوندِ توکن درست است", tok.startsWith(API_TOKEN_PREFIX));
const payload = JSON.parse(Buffer.from(parts[1], "base64url").toString("utf8"));
t("آدرسِ پنل داخلِ خودِ توکن است", payload.u === ORIGIN, payload.u);
t("نامِ توکن داخلِ پیلود است", payload.n === "telegram-bot", payload.n);
t("شناسهٔ توکن با ردیفِ دیتابیس می‌خواند", Number(parts[2]) === made.info.id, parts[2] + " vs " + made.info.id);

// ③ راز در دیتابیس لو نمی‌رود
const row = db.prepare("SELECT * FROM api_tokens WHERE id = ?").get(made.info.id);
t("راز به‌شکلِ متنِ خام ذخیره نمی‌شود", !String(row.hash).includes(parts[3]), String(row.hash).slice(0, 16) + "…");
t("فقط پیشوندِ کوتاه برای شناسایی ذخیره می‌شود", row.prefix === parts[3].slice(0, 6));

// ④ اعتبارسنجی
t("توکنِ معتبر تأیید می‌شود", verifyApiToken(tok).ok === true && verifyApiToken(tok).name === "telegram-bot");
t("رازِ دست‌کاری‌شده رد می‌شود", verifyApiToken(`srb1.${parts[1]}.${parts[2]}.${parts[3]}XX`).ok === false);
t("توکنِ JWT/تصادفی رد می‌شود", verifyApiToken("eyJhbGciOiJIUzI1NiJ9.abc.def").ok === false);
t("توکنِ ناقص رد می‌شود", verifyApiToken("srb1.only-two").ok === false);

// ⑤ ابطال
t("فهرست توکن‌ها ثبت‌شده را نشان می‌دهد", listApiTokens().some((x) => x.id === made.info.id));
revokeApiToken(made.info.id);
t("توکنِ ابطال‌شده دیگر کار نمی‌کند", verifyApiToken(tok).ok === false);
const again = createApiToken("second", ORIGIN);
t("توکنِ دوم مستقل کار می‌کند", verifyApiToken(again.token).ok === true && verifyApiToken(tok).ok === false);
deleteApiToken(again.info.id);
t("حذفِ توکن از دیتابیس", !listApiTokens().some((x) => x.id === again.info.id));

// ⑥ تشخیصِ آدرسِ عمومی از هدرها (همان چیزی که در توکن می‌نشیند)
t("آدرس از x-forwarded-* خوانده می‌شود",
  originFromHeaders({ "x-forwarded-proto": "https", "x-forwarded-host": "p.example.com" }) === "https://p.example.com");
t("آدرس از host خوانده می‌شود", originFromHeaders({ host: "h.example.com" }) === "https://h.example.com");
t("hostِ نامعتبر قبول نمی‌شود", originFromHeaders({ host: "bad host/../x" }) === "");

// ⑦ دست‌دادنِ ربات: شمارش‌ها
db.exec("DELETE FROM inbounds; DELETE FROM users;");
db.prepare("INSERT INTO inbounds (tag, label, protocol, transport, port, path, host, enabled, created_at) VALUES (?,?,?,?,?,?,?,?,?)")
  .run("1 | هلند 🇳🇱", "1 | هلند 🇳🇱", "vless", "ws", 20000, "/wpnfa/ws-AAAA", "", 1, Date.now());
db.prepare("INSERT INTO users (email, uuid, password, sub_token, fingerprint, alpn, data_limit, ip_limit, enabled, up, down, comment, telegram_id, last_reset, created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)")
  .run("u1", "uuid-1", "pw", "subtok-1", "chrome", "h2", 1073741824, 0, 1, 1000, 2000, "", "", 0, Date.now());
const hs = panelHandshake(ORIGIN);
t("دست‌دادن نام/آدرس/نسخه می‌دهد", hs.ok === true && hs.url === ORIGIN && !!hs.version && hs.app === "SideRail");
t("اینباندها با نامِ نمایشی برمی‌گردند", hs.inbounds.length === 1 && hs.inbounds[0].label === "1 | هلند 🇳🇱", JSON.stringify(hs.inbounds[0] || {}));
t("شمارشِ کاربران درست است", hs.users.total === 1 && hs.users.enabled === 1, JSON.stringify(hs.users));
t("ترافیکِ کل درست است", hs.traffic.up === 1000 && hs.traffic.down === 2000, JSON.stringify(hs.traffic));

console.log("\n" + (fail === 0 ? "✅ همهٔ " + pass + " آزمون سبز" : "❌ " + fail + " ناموفق از " + (pass + fail)));
process.exit(fail === 0 ? 0 : 1);
