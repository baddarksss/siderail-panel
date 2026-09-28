# وصله‌های ما روی SideRail — جای دقیقِ هر تغییر

| فایل | تغییر |
|---|---|
| `apps/server/src/types.ts` | `Inbound.label` اضافه شد |
| `apps/server/src/db.ts` | در `migrateColumns()`: ستونِ `label` روی جدولِ `inbounds` (ALTER TABLE امن) |
| `apps/server/src/inbounds.ts` | بذر با `label=tag` · `updateInbound(id,{tag,label,path})` · `normalizeInboundPath()` |
| `apps/server/src/links.ts` | `label()` ⇒ `inbound.label \|\| inbound.tag` (بدونِ برند) |
| `apps/server/src/sub.ts` | `subProfileTitle()` از تنظیمِ `sub_title` (خالی ⇒ ایمیل) — ۲ جای هدر |
| `apps/server/src/sub-formats.ts` | نامِ پروکسی = label · نامِ گروهِ Clash و سلکتورِ Sing-box = عنوانِ ساب (پیش‌فرض `Proxy`) |
| `apps/server/src/routes.ts` | `PATCH /api/inbounds/:id` پذیرای `{enabled?,tag?,label?,path?}` با اعتبارسنجی · پیش‌فرضِ `subTitle` خالی |
| `apps/web/src/lib/types.ts` · `api.ts` | `label` در نوع + متدِ `updateInbound` |
| `apps/web/src/pages/inbounds.tsx` | نمایشِ نامِ نمایشی + دیالوگِ ویرایش (label/tag/path) |
| `apps/web/src/lib/i18n.tsx` | کلیدهای `inboundLabel` · `inboundTag` · `inboundEditTitle` · `inboundEditHint` · `inboundSaved` (en/ru/zh) |

## پاسخِ دو پرسشِ کارفرما (از خودِ سورس)
**۱) اگر تگِ اینباند عوض شود، کانفیگ به‌هم می‌ریزد؟** نه.
`tag` فقط شناسهٔ داخلیِ Xray و کلیدِ آمارِ اینباند (`inbound_traffic.inbound_tag`) است؛
لینکِ کاربران به `path`/`port` تکیه می‌کند و قاعده‌های routing با `id` نگاشت می‌شوند
(`tagById` در `xray-config.ts`). پس تغییرِ تگ ⇒ فقط «ری‌استارتِ Xray + شروعِ آمارِ نو برای آن اینباند».
آزمونِ زنده: تگِ `VMess-WS` ⇒ `DE-Fast` · Xray سالم (`running`, uptime ۵s) · نامِ کانفیگِ کاربر شد `DE-Fast` · سپس برگشت.

**۲) مسیر (path) حتماً باید شاملِ «SideRail» باشد؟** نه — کاملاً آزاد است.
`tunnel.ts → matchInbound()` فقط تطبیقِ دقیق/پیشوندی با همان مسیرِ ثبت‌شده را چک می‌کند؛
فقط نباید با مسیرهای خودِ اپ تداخل کند: `/api` · `/sub` · `/assets` · `/favicon` · `/healthz`.
حالا از پنل (آیکنِ ✏️ روی کارتِ اینباند) یا با API قابلِ ویرایش است.

## قیدهای اعتبارسنجی
- `tag`: حرف/عدد/فاصله/`_ . -` · ۱..۳۲ نویسه · یکتا
- `label`: تا ۴۸ نویسه (ایموجی مجاز) · خالی = استفاده از tag
- `path`: با `/` شروع شود، ۲..۶۴ نویسه، ۱..۴ بخش، یکتا، مسیرهای رزروشده ممنوع

## وصله‌های ۱۲–۱۶ (۲۰۲۶-۰۹-۲۹) — ویرایشِ اینباند از پنل + بکاپ (۱۳–۱۶ بعداً با وصلهٔ ۲۲ تکمیل شد)
| # | وصله | فایل |
|---|---|---|
| ۱۲ | تگِ آزاد: `tag` تا ۴۰ کاراکتر با فارسی/ایموجی/`\|` (فقط کاراکترهای کنترلی و `"'\`\<>` ممنوع) | `inbounds.ts` |
| ۱۳ | ری‌استورِ بکاپ: ستونِ `label` هم نوشته می‌شود (قبلاً جا می‌افتاد) | `backup.ts` |
| ۱۴ | گزینهٔ `freshPaths` در ری‌استور: فقط پیشوندِ اولِ مسیر از بکاپ می‌ماند و بخشِ آخر تازه تولید می‌شود (`/wpnfa/ws-XtN9GOHe` ⇒ `/wpnfa/ws-<8 random>`) | `backup.ts`, `routes.ts` |
| ۱۵ | چک‌باکسِ «مسیرهای تازه» در صفحهٔ داشبورد + `?freshPaths=1` | `dashboard.tsx`, `api.ts` |
| ۱۶ | رشته‌های سه‌زبانه برای گزینهٔ بالا | `i18n.tsx` |

آزمون‌ها: `patches/tests/backup.test.mjs` ⇒ **۳۶/۳۶** (پس از وصلهٔ ۲۲ — با `/tmp/node22/bin/node --experimental-sqlite`).

## وصله‌های ۱۷–۲۱ (۲۰۲۶-۰۹-۲۹) — 🔑 توکنِ دسترسیِ ربات («آدرس و رمز نده؛ فقط توکن بده»)
| # | وصله | فایل |
|---|---|---|
| ۱۷ | ماژولِ توکن: ساخت/فهرست/ابطال/اعتبارسنجی + «دست‌دادن» (نام/آدرس/اینباندها/کاربران/ترافیک) | `apps/server/src/api-tokens.ts` (تازه) |
| ۱۸ | جدولِ `api_tokens` (راز فقط به‌شکلِ sha256) در `migrate()` | `apps/server/src/db.ts` |
| ۱۹ | `authGuard` توکنِ `srb1.…` را مثلِ JWT می‌پذیرد (Authorization: Bearer) ⇒ همهٔ `/api` | `apps/server/src/auth.ts` |
| ۲۰ | مسیرهای `GET/POST /api/api-tokens` · `DELETE /api/api-tokens/:id` · `GET /api/bot/handshake` | `apps/server/src/routes.ts` |
| ۲۱ | بخشِ «Bot access token» در صفحهٔ ربات (ساخت + کپی + ابطال) + متدهای API + ترجمه‌های en/ru/zh | `apps/web/src/components/api-token-card.tsx` (تازه) · `pages/bot.tsx` · `lib/api.ts` · `lib/types.ts` · `lib/i18n.tsx` |

**شکلِ توکن:** `srb1.<base64url({u:آدرس,n:نام,t:زمان})>.<id>.<secret>`
⇒ رباتِ بیرونی آدرسِ پنل را از خودِ توکن می‌خواند؛ نیازی به آدرس/نام‌کاربری/رمز نیست.

آزمون‌ها: `patches/tests/bot-token.test.mjs` ⇒ **۲۴/۲۴** · `backup.test.mjs` ⇒ **۳۶/۳۶**
(اجرا: `/tmp/node22/bin/node --experimental-sqlite patches/tests/<file>`)
بازتولیدپذیری: `python3 patches/panel-patch.py` روی نسخهٔ تازهٔ upstream بدونِ diff اجرا می‌شود
(خروجی، بایت‌به‌بایت با همین ریپو یکی است).

## وصلهٔ ۲۲ (۲۰۲۶-۰۹-۲۹) — 💾 «بکاپِ سبک»: فقط تنظیمات، نه لیستِ مشتریان + مسیرِ کوتاه
خواستهٔ کارفرما: «کاربر‌ها تو بکاپ می‌آیند — بکاپ فقط تنظیمات باشد، نه لیستِ کلاینت‌ها» و
«قرار بود در بکاپ مسیر فقط `wpnfa` بماند، ولی کلِ مسیر را گرفته بود».

| تغییر | جزئیات | فایل |
|---|---|---|
| خروجیِ پیش‌فرض = سبک | `/api/backup/export` دیگر `users`/`user_inbounds`/`admins` نمی‌دهد؛ فقط `inbounds` + `settings` (+`version`/`exported_at`). بکاپِ کاملِ قبلی با `?full=1` | `backup.ts` · `routes.ts` |
| مسیرِ کوتاه در بکاپ | `firstPathSegment()` ⇒ `/wpnfa/ws-YWZ5weA_` در فایل می‌شود `/wpnfa` (مسیرِ کامل = کلیدِ زندهٔ تونل؛ نباید در فایلِ جابه‌جاشدنی بیفتد) | `backup.ts` |
| ری‌استور | مسیرِ تک‌بخشی قاعدهٔ ایمن دارد: اگر پنل از قبل اینباندی با همان شناسه و همان پیشوند دارد **همان مسیرِ زنده دست‌نخورده می‌ماند** (کانفیگِ کاربرانِ فعلی نمی‌شکند)؛ روی پنلِ تازه/خالی یا با چک‌باکسِ «مسیرهای تازه» ⇒ `/wpnfa/ws-<۸ رندوم>`. مسیرهای دوبخشیِ بکاپ‌های قدیمی فقط با همان چک‌باکس عوض می‌شوند | `backup.ts` |
| کاربران در ری‌استورِ سبک | اگر فایل کاربران نداشته باشد، **لیستِ کاربرانِ فعلی پاک نمی‌شود** و پیوندِ کاربر↔اینباند (که با حذفِ اینباند آبشاری پاک می‌شد) برمی‌گردد | `backup.ts` |
| بکاپِ روزانهٔ تلگرام | `bot.ts` هم از همین تابع می‌آید ⇒ حالا سبک است | `bot.ts` (بدونِ تغییر؛ اثرِ جانبی) |
| UI | کارتِ «Export backup» متنِ تازه + لینکِ کوچکِ «Full backup (incl. clients)» (`exportBackupUrl(true)`) · هشدارِ ری‌استور به‌روز شد | `dashboard.tsx` · `lib/api.ts` · `lib/i18n.tsx` (en/ru/zh) |

**آزمونِ زنده (سرورِ محلی + HTTP):** `export` ⇒ مسیرها `["/SideRail","/SideRail",…]` و `users:0`/`admins:0` ·
`export?full=1` ⇒ `users:1`/`admins:1` · ری‌استورِ فایلِ سبک ⇒ `{ok:true, users:0, inbounds:5, freshPaths:5}` و
کاربرانِ موجود (`keepme`, `sample-user`) **باقی ماندند** و مسیرها تازه شدند.
آزمونِ واحد: `patches/tests/backup.test.mjs` ⇒ **۳۶/۳۶** (۲۵ آزمونِ تازهٔ همین وصله).
آزمونِ زندهٔ سرور (HTTP): ری‌استورِ فایلِ سبک روی همان پنل ⇒ `freshPaths:0` و مسیرها **بیت‌به‌بیت دست‌نخورده** و کاربران سالم؛
ری‌استور روی پنلِ دیگر (پیشوندِ متفاوت) ⇒ `freshPaths:5` و مسیرهای `/other/ws-xxxxxxxx`.
