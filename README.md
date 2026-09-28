# siderail-panel — سورسِ وصله‌خوردهٔ پنلِ SideRail (نصبِ خودکار روی Railway)

این ریپو = **سورسِ اصلیِ [icubaby/SideRail](https://github.com/icubaby/SideRail) + وصله‌های ما**.
هدف: پنل با رباتِ مدیریتِ xpanel کامل مچ باشد و بتوان روی نسخه‌های تازهٔ upstream هم به‌روزرسانی کرد.

## وصله‌ها (همه در `patches/panel-patch.py`)
| # | چه می‌کند |
|---|---|
| ۱ | **نامِ کانفیگ‌ها = «نامِ نمایشیِ اینباند» (label)** وگرنه `tag` — پیشوندِ برند («icubaby/SideRail - ») حذف شد |
| ۲ | **عنوانِ سابسکریپشن** دیگر برند نیست؛ از تنظیمِ «عنوان ساب» می‌آید (خالی ⇒ فقط ایمیلِ کاربر) |
| ۳ | **ویرایشِ اینباند از پنل**: نامِ نمایشی · تگ · مسیر (مسیر کاملاً قابلِ شخصی‌سازی است؛ «SideRail» لازم نیست) |
| ۴ | نامِ پروکسی‌های Clash/Sing-box هم از label می‌آید |
| ۵ | مهاجرتِ خودکارِ دیتابیس (ستونِ `label`) — بدونِ از دست رفتنِ داده |

## نصب روی Railway
1. `New Project → Deploy from GitHub repo` و همین ریپو را انتخاب کن (Dockerfile خودش بیلد می‌شود).
2. `Settings → Volumes` ⇒ **Volume روی `/data`** (اجباری — وگرنه هر دیپلوی کاربران را پاک می‌کند).
3. `Settings → Networking → Generate Domain` ⇒ پورت `8080`.
4. صفحهٔ Setup ⇒ ساختِ حسابِ مالک.

## به‌روزرسانی از upstream (بدونِ گم‌شدنِ وصله‌ها)
```bash
./apply_upstream.sh          # آخرین سورسِ upstream را می‌آورد و وصله‌های ما را رویش اعمال می‌کند
npm ci && npm run typecheck && npm run build     # (اختیاری — برای اطمینانِ محلی)
git add -A && git commit -m "sync upstream + patches" && git push
```
`apply_upstream.sh` فقط فایل‌های `apps/`, `Dockerfile`, ... را از upstream می‌گیرد و بعد
`patches/panel-patch.py` را اجرا می‌کند. اگر upstream ساختار را عوض کند، اسکریپت با پیامِ
«لنگر پیدا نشد» متوقف می‌شود (هیچ‌وقت خرابیِ بی‌صدا).

## نکته‌های حقوقی
سورسِ اصلی تحتِ «SideRail Proprietary License» است و برداشتنِ امضای نویسنده ممنوع است.
ما فقط **نامِ نمایشیِ کانفیگ و عنوانِ سابِ سمتِ کلاینت** را قابلِ تنظیم کرده‌ایم؛ امضاها
(`X-Powered-By`, `/healthz`, لاگِ بوت, هدرِ فایل‌ها) دست‌نخورده‌اند.
