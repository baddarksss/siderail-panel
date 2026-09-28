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

## وصله‌های ۱۲–۱۶ (۲۰۲۶-۰۹-۲۹) — ویرایشِ اینباند از پنل + بکاپِ کامل
| # | وصله | فایل |
|---|---|---|
| ۱۲ | تگِ آزاد: `tag` تا ۴۰ کاراکتر با فارسی/ایموجی/`\|` (فقط کاراکترهای کنترلی و `"'\`\<>` ممنوع) | `inbounds.ts` |
| ۱۳ | ری‌استورِ بکاپ: ستونِ `label` هم نوشته می‌شود (قبلاً جا می‌افتاد) | `backup.ts` |
| ۱۴ | گزینهٔ `freshPaths` در ری‌استور: فقط پیشوندِ اولِ مسیر از بکاپ می‌ماند و بخشِ آخر تازه تولید می‌شود (`/wpnfa/ws-XtN9GOHe` ⇒ `/wpnfa/ws-<8 random>`) | `backup.ts`, `routes.ts` |
| ۱۵ | چک‌باکسِ «مسیرهای تازه» در صفحهٔ داشبورد + `?freshPaths=1` | `dashboard.tsx`, `api.ts` |
| ۱۶ | رشته‌های سه‌زبانه برای گزینهٔ بالا | `i18n.tsx` |

آزمون‌ها: `patches/tests/backup.test.mjs` ⇒ **۱۱/۱۱** (با `/tmp/node22/bin/node --experimental-sqlite`).
