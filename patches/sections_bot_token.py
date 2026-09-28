# ═════════════════════════════════════════════════════════════════════════════
#  ۱۷–۲۱) 🔑 توکنِ دسترسیِ ربات — «آدرس و رمز نده؛ فقط توکن بده»
#
#  چه می‌کند: در صفحهٔ «ربات تلگرام» یک بخشِ تازه اضافه می‌شود که توکن می‌سازد.
#  خودِ توکن آدرسِ عمومیِ همین پنل را در خودش دارد ⇒ رباتِ مدیریت فقط با همان
#  توکن همهٔ /api را می‌خواند (بدونِ آدرس، نام‌کاربری و رمز).
#
#  این فایل با exec داخلِ panel-patch.py اجرا می‌شود (به sub/copy_new_file/… دسترسی دارد)
# ═════════════════════════════════════════════════════════════════════════════

def copy_new_file(rel_src, rel_dst, label):
    """نوشتنِ یک فایلِ تازه (بدونِ لنگر) — اگر محتوا یکی بود، کاری نمی‌کند."""
    _src = os.path.join(os.path.dirname(os.path.abspath(__file__)), rel_src.replace("patches/", "", 1))
    _dst = os.path.join(ROOT, rel_dst)
    if not os.path.exists(_src):
        print(f"❌ {label}: فایلِ منبع پیدا نشد ({rel_src})"); sys.exit(1)
    _new = io.open(_src, encoding="utf-8").read()
    _old = io.open(_dst, encoding="utf-8").read() if os.path.exists(_dst) else ""
    if _old == _new:
        done.append(label + " (از قبل)"); return
    if not CHECK:
        os.makedirs(os.path.dirname(_dst), exist_ok=True)
        io.open(_dst, "w", encoding="utf-8").write(_new)
    done.append(label)


# ۱۷) دو فایلِ تازه: ماژولِ سرور + کارتِ وب
copy_new_file("patches/files/api-tokens.ts", "apps/server/src/api-tokens.ts",
              "server/api-tokens.ts: توکنِ ربات (ساخت/اعتبارسنجی/ابطال + دست‌دادن)")

copy_new_file("patches/files/api-token-card.tsx", "apps/web/src/components/api-token-card.tsx",
              "web/api-token-card.tsx: بخشِ «توکنِ دسترسیِ ربات»")

# ۱۸) db.ts: جدولِ api_tokens
sub("apps/server/src/db.ts",
    '    CREATE TABLE IF NOT EXISTS inbound_traffic (\n'
    '      inbound_tag TEXT PRIMARY KEY,\n'
    '      up INTEGER NOT NULL DEFAULT 0,\n'
    '      down INTEGER NOT NULL DEFAULT 0\n'
    '    );',
    '    CREATE TABLE IF NOT EXISTS inbound_traffic (\n'
    '      inbound_tag TEXT PRIMARY KEY,\n'
    '      up INTEGER NOT NULL DEFAULT 0,\n'
    '      down INTEGER NOT NULL DEFAULT 0\n'
    '    );\n'
    '\n'
    '    -- 🔑 توکنِ دسترسیِ رباتِ مدیریت (بدونِ نیاز به نام‌کاربری/رمز) — راز فقط به‌شکلِ hash\n'
    '    CREATE TABLE IF NOT EXISTS api_tokens (\n'
    '      id INTEGER PRIMARY KEY AUTOINCREMENT,\n'
    "      name TEXT NOT NULL DEFAULT '',\n"
    "      prefix TEXT NOT NULL DEFAULT '',\n"
    '      hash TEXT NOT NULL,\n'
    '      created_at INTEGER NOT NULL,\n'
    '      last_used_at INTEGER NOT NULL DEFAULT 0,\n'
    '      used_count INTEGER NOT NULL DEFAULT 0,\n'
    '      revoked_at INTEGER\n'
    '    );\n'
    '    CREATE INDEX IF NOT EXISTS idx_api_tokens_hash ON api_tokens(hash);',
    "db.ts: جدولِ api_tokens")

# ۱۹) auth.ts: پذیرشِ توکنِ srb1 روی همهٔ مسیرها
sub("apps/server/src/auth.ts",
    'import { db, getSetting, setSetting } from "./db.js";',
    'import { db, getSetting, setSetting } from "./db.js";\n'
    'import { API_TOKEN_PREFIX, verifyApiToken, touchApiToken } from "./api-tokens.js";',
    "auth.ts: importِ توکنِ ربات")

sub("apps/server/src/auth.ts",
    'export interface AuthedRequest extends Request {\n  admin?: AdminInfo;\n}',
    'export interface AuthedRequest extends Request {\n'
    '  admin?: AdminInfo;\n'
    '  /** شناسهٔ توکنِ ربات — اگر درخواست با توکنِ ماشین آمده باشد (نه سشنِ ادمین) */\n'
    '  apiTokenId?: number;\n'
    '}',
    "auth.ts: فیلدِ apiTokenId")

sub("apps/server/src/auth.ts",
    '  try {\n'
    '    const payload = jwt.verify(token, config.jwtSecret) as { id: number; tv?: number };',
    '  // 🔑 توکنِ ربات (srb1.…) — مسیرِ دومِ احراز هویت: بدونِ نام‌کاربری/رمز، روی همهٔ /api کار می‌کند.\n'
    '  if (token.startsWith(API_TOKEN_PREFIX)) {\n'
    '    const hit = verifyApiToken(token);\n'
    '    if (!hit.ok || !hit.id) {\n'
    '      res.status(401).json({ error: "unauthorized" });\n'
    '      return;\n'
    '    }\n'
    '    touchApiToken(hit.id);\n'
    '    // اختیاراتِ توکن = مالکِ پنل (ربات همان کارهایی را می‌کند که ادمین با پنل می‌کرد)\n'
    '    const owner = db\n'
    '      .prepare("SELECT id, username, created_at FROM admins WHERE role = \'owner\' ORDER BY id ASC LIMIT 1")\n'
    '      .get() as { id: number; username: string; created_at: number } | undefined;\n'
    '    req.admin = {\n'
    '      id: owner?.id ?? 0,\n'
    '      username: "bot:" + (hit.name || "token"),\n'
    '      role: "owner",\n'
    '      permissions: ALL_PERMISSIONS,\n'
    '      dataLimit: 0,\n'
    '      createdAt: owner?.created_at ?? 0,\n'
    '    };\n'
    '    req.apiTokenId = hit.id;\n'
    '    next();\n'
    '    return;\n'
    '  }\n'
    '  try {\n'
    '    const payload = jwt.verify(token, config.jwtSecret) as { id: number; tv?: number };',
    "auth.ts: مسیرِ توکنِ ربات در authGuard")

# ۲۰) routes.ts: چهار مسیرِ توکن + دست‌دادنِ ربات
sub("apps/server/src/routes.ts",
    'import { db, getSetting, setSetting } from "./db.js";',
    'import { db, getSetting, setSetting } from "./db.js";\n'
    'import {\n'
    '  listApiTokens,\n'
    '  createApiToken,\n'
    '  revokeApiToken,\n'
    '  originFromHeaders,\n'
    '  panelHandshake,\n'
    '} from "./api-tokens.js";',
    "routes.ts: importِ توکنِ ربات")

sub("apps/server/src/routes.ts",
    "void db;",
    '// ─────────────────────────────────────────────────────────────────────────────\n'
    '// 🔑 توکنِ ربات (API Token) — وصلهٔ ما\n'
    '//   ادمین در صفحهٔ «ربات تلگرام» یک توکن می‌سازد و همان را به رباتِ مدیریت می‌دهد؛\n'
    '//   آدرسِ عمومیِ پنل داخلِ خودِ توکن است، پس ربات نه آدرس می‌پرسد نه نام‌کاربری/رمز.\n'
    '//   خودِ توکن در authGuard همهٔ مسیرهای /api را باز می‌کند (Authorization: Bearer).\n'
    '// ─────────────────────────────────────────────────────────────────────────────\n'
    'api.get("/api-tokens", requirePermission("bot"), (req, res) => {\n'
    '  res.json({\n'
    '    tokens: listApiTokens(),\n'
    '    url: originFromHeaders(req.headers as unknown as Record<string, unknown>),\n'
    '  });\n'
    '});\n'
    '\n'
    'api.post("/api-tokens", requirePermission("bot"), (req: AuthedRequest, res) => {\n'
    '  const body = z.object({ name: z.string().max(40).optional() }).safeParse(req.body ?? {});\n'
    '  if (!body.success) {\n'
    '    res.status(400).json({ error: "invalid input" });\n'
    '    return;\n'
    '  }\n'
    '  const created = createApiToken(\n'
    '    body.data.name || "bot",\n'
    '    originFromHeaders(req.headers as unknown as Record<string, unknown>),\n'
    '  );\n'
    '  if (!created.ok || !created.token) {\n'
    '    res.status(400).json({ error: created.error || "could not create token" });\n'
    '    return;\n'
    '  }\n'
    '  logActivity(req.admin!.username, "api_token_create", `#${created.info?.id ?? 0}`);\n'
    '  res.json({ ok: true, token: created.token, info: created.info });\n'
    '});\n'
    '\n'
    'api.delete("/api-tokens/:id", requirePermission("bot"), (req: AuthedRequest, res) => {\n'
    '  const done = revokeApiToken(Number(req.params.id));\n'
    '  if (!done.ok) {\n'
    '    res.status(404).json({ error: done.error || "not found" });\n'
    '    return;\n'
    '  }\n'
    '  logActivity(req.admin!.username, "api_token_revoke", `#${req.params.id}`);\n'
    '  res.json({ ok: true });\n'
    '});\n'
    '\n'
    '// 🤝 دست‌دادن: ربات با همان توکن در یک درخواست، نام/آدرس/اینباندها/کاربران/ترافیک را می‌خواند.\n'
    'api.get("/bot/handshake", requirePermission("dashboard"), (req, res) => {\n'
    '  res.json(panelHandshake(originFromHeaders(req.headers as unknown as Record<string, unknown>)));\n'
    '});\n'
    '\n'
    'void db;',
    "routes.ts: مسیرهای /api-tokens و /bot/handshake")

# ۲۱) وب: کلاینت + نوع + کارت در صفحهٔ ربات + ترجمه‌ها
sub("apps/web/src/lib/types.ts",
    "export interface BotConfig {",
    '/** 🔑 توکنِ دسترسیِ ربات (وصلهٔ ما) — همان که در صفحهٔ ربات ساخته می‌شود */\n'
    'export interface ApiTokenInfo {\n'
    '  id: number;\n'
    '  name: string;\n'
    '  prefix: string;\n'
    '  createdAt: number;\n'
    '  lastUsedAt: number;\n'
    '  usedCount: number;\n'
    '  revokedAt: number | null;\n'
    '}\n'
    '\n'
    'export interface ApiTokenList {\n'
    '  tokens: ApiTokenInfo[];\n'
    '  url: string;\n'
    '}\n'
    '\n'
    'export interface BotConfig {',
    "web/types.ts: نوعِ توکن")

sub("apps/web/src/lib/api.ts",
    '  testBot: (token: string, chatIds: string[]) =>\n'
    '    request("/api/bot/test", { method: "POST", body: JSON.stringify({ token, chatIds }) }),\n'
    '};',
    '  testBot: (token: string, chatIds: string[]) =>\n'
    '    request("/api/bot/test", { method: "POST", body: JSON.stringify({ token, chatIds }) }),\n'
    '  // 🔑 توکنِ دسترسیِ ربات: ساخت/فهرست/ابطال — بدونِ نیاز به آدرس و نام‌کاربری در ربات\n'
    '  listApiTokens: () => request<import("./types").ApiTokenList>("/api/api-tokens"),\n'
    '  createApiToken: (name: string) =>\n'
    '    request<{ ok: boolean; token: string; info: import("./types").ApiTokenInfo }>(\n'
    '      "/api/api-tokens",\n'
    '      { method: "POST", body: JSON.stringify({ name }) },\n'
    '    ),\n'
    '  revokeApiToken: (id: number) => request(`/api/api-tokens/${id}`, { method: "DELETE" }),\n'
    '};',
    "web/api.ts: متدهای توکن")

sub("apps/web/src/pages/bot.tsx",
    'import type { BotConfig } from "@/lib/types";',
    'import type { BotConfig } from "@/lib/types";\n'
    'import { ApiTokenCard } from "@/components/api-token-card";',
    "web/bot.tsx: importِ کارتِ توکن")

sub("apps/web/src/pages/bot.tsx",
    '        </CardContent>\n      </Card>\n    </div>\n  );\n}',
    '        </CardContent>\n      </Card>\n'
    '\n'
    '      {/* 🔑 توکنِ دسترسیِ ربات — وصلهٔ ما */}\n'
    '      <ApiTokenCard />\n'
    '    </div>\n  );\n}',
    "web/bot.tsx: نمایشِ کارتِ توکن")

I18N3 = {
    "en": {
        "refresh": "Refresh",
        "apiTokenSection": "Bot access token",
        "apiTokenSectionDesc": "Create a token and paste it into your Telegram bot — no URL, username or password needed. The token already contains this panel's address.",
        "apiTokenName": "Token name",
        "apiTokenCreate": "Create token",
        "apiTokenCreating": "Creating…",
        "apiTokenShownOnce": "Copy this token now — it is shown only once:",
        "apiTokenHowTo": "Send this token to the bot (➕ Add panel). The bot reads the address, inbounds and users by itself.",
        "apiTokenEmpty": "No tokens yet.",
        "apiTokenRevoke": "Revoke",
        "apiTokenRevokedTag": "revoked",
        "apiTokenActiveTag": "active",
        "apiTokenCreatedAt": "created",
        "apiTokenLastUsed": "last used",
        "apiTokenCalls": "calls",
        "apiTokenHint": "Anyone holding this token has full access to this panel — keep it private and revoke it if leaked.",
        "apiTokenCreated": "Token created",
        "apiTokenRevoked": "Token revoked",
    },
    "ru": {
        "apiTokenSection": "Токен доступа для бота",
        "apiTokenSectionDesc": "Создайте токен и вставьте его в своего Telegram-бота — адрес, логин и пароль не нужны: адрес панели уже внутри токена.",
        "apiTokenName": "Название токена",
        "apiTokenCreate": "Создать токен",
        "apiTokenCreating": "Создание…",
        "apiTokenShownOnce": "Скопируйте токен сейчас — он показывается только один раз:",
        "apiTokenHowTo": "Отправьте этот токен боту (➕ Добавить панель). Бот сам прочитает адрес, инбаунды и пользователей.",
        "apiTokenEmpty": "Токенов пока нет.",
        "apiTokenRevoke": "Отозвать",
        "apiTokenRevokedTag": "отозван",
        "apiTokenActiveTag": "активен",
        "apiTokenCreatedAt": "создан",
        "apiTokenLastUsed": "последнее использование",
        "apiTokenCalls": "запросов",
        "apiTokenHint": "У кого есть этот токен — у того полный доступ к панели. Держите его в секрете и отзовите при утечке.",
        "apiTokenCreated": "Токен создан",
        "apiTokenRevoked": "Токен отозван",
        "refresh": "Обновить",
    },
    "zh": {
        "apiTokenSection": "机器人访问令牌",
        "apiTokenSectionDesc": "创建一个令牌并粘贴到你的 Telegram 机器人：无需地址、用户名或密码，面板地址已包含在令牌中。",
        "apiTokenName": "令牌名称",
        "apiTokenCreate": "创建令牌",
        "apiTokenCreating": "创建中…",
        "apiTokenShownOnce": "请立即复制该令牌 — 只显示一次：",
        "apiTokenHowTo": "把此令牌发给机器人（➕ 添加面板）。机器人会自行读取地址、入站和用户。",
        "apiTokenEmpty": "还没有令牌。",
        "apiTokenRevoke": "撤销",
        "apiTokenRevokedTag": "已撤销",
        "apiTokenActiveTag": "有效",
        "apiTokenCreatedAt": "创建于",
        "apiTokenLastUsed": "最后使用",
        "apiTokenCalls": "调用",
        "apiTokenHint": "持有此令牌即拥有面板的完整权限 — 请妥善保管，泄露时请撤销。",
        "apiTokenCreated": "令牌已创建",
        "apiTokenRevoked": "令牌已撤销",
        "refresh": "刷新",
    },
}
_t3 = read("apps/web/src/lib/i18n.tsx")
_our3 = sorted({k for blk in I18N3.values() for k in blk})
for _k in _our3:
    _t3 = re.sub(r"^\s*" + re.escape(_k) + r":.*\n", "", _t3, flags=re.M)
_i3_marker = {"en": '  botToken: "Bot token",\n',
              "ru": '  botToken: "Токен бота",\n',
              "zh": '  botToken: "机器人令牌",\n'}
for _lang, _blk in I18N3.items():
    _marker = _i3_marker[_lang]
    if _marker not in _t3:
        print(f"❌ i18n3 ({_lang}): لنگر پیدا نشد"); sys.exit(1)
    _t3 = _t3.replace(_marker, _marker + "".join(
        f"  {_k}: " + json.dumps(_v, ensure_ascii=False) + ",\n" for _k, _v in _blk.items()), 1)
if not CHECK:
    write("apps/web/src/lib/i18n.tsx", _t3)
done.append("web/i18n.tsx: کلیدهای توکنِ ربات (en/ru/zh)")
