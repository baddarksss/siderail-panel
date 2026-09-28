import { db } from "./db.js";
import { nanoid } from "nanoid";
import type { Inbound, UserRecord } from "./types.js";

/** 🧩 (وصلهٔ ما) فقط «بخشِ اول» مسیر را نگه می‌دارد: ‎/wpnfa/ws-x‎ ⇒ ‎/wpnfa‎
 *  چرا: مسیرِ کامل، کلیدِ زندهٔ تونلِ کاربران است و نباید در فایلِ بکاپ بیفتد.
 *  دمِ رندوم هنگامِ ری‌استور تازه ساخته می‌شود. مسیرِ خالی دست‌نخورده می‌ماند. */
export function firstPathSegment(path: unknown): string {
  const seg = String(path || "").split("/").filter(Boolean);
  return seg.length ? "/" + seg[0] : String(path || "");
}


interface AdminBackup {
  id: number;
  username: string;
  password_hash: string;
  role: string;
  permissions: string;
  data_limit: number;
  created_at: number;
}

interface BackupPayload {
  version: number;
  exported_at: number;
  users: UserRecord[];
  user_inbounds: { user_id: number; inbound_id: number }[];
  inbounds: Inbound[];
  admins?: AdminBackup[];
  settings?: { key: string; value: string }[];
}

/** 🧩 (وصلهٔ ما) بکاپِ سبک = «فقط تنظیمات».
 *  • `settingsOnly !== false` (پیش‌فرض): لیستِ مشتریان (`users`/`user_inbounds`)
 *    و `admins` در فایل نمی‌آید ⇒ بکاپِ قابلِ جابه‌جایی.
 *  • مسیرِ اینباندها فقط بخشِ اولشان ذخیره می‌شود (‎/wpnfa‎).
 *  • برای بکاپِ کاملِ قبلی: `exportData({ settingsOnly: false })` یا `?full=1`. */
export function exportData(options: { settingsOnly?: boolean } = {}): BackupPayload {
  const settingsOnly = options.settingsOnly !== false;
  const users = settingsOnly
    ? []
    : (db.prepare("SELECT * FROM users").all() as unknown as UserRecord[]);
  const inbounds = (db.prepare("SELECT * FROM inbounds").all() as unknown as Inbound[]).map(
    (ib) => ({ ...ib, path: firstPathSegment(ib.path) }),
  );
  const links = settingsOnly
    ? []
    : (db.prepare("SELECT user_id, inbound_id FROM user_inbounds").all() as unknown as {
        user_id: number;
        inbound_id: number;
      }[]);
  const admins = settingsOnly
    ? []
    : (db.prepare("SELECT * FROM admins").all() as unknown as AdminBackup[]);
  const settings = db.prepare("SELECT key, value FROM settings").all() as unknown as {
    key: string;
    value: string;
  }[];
  return {
    version: 2,
    exported_at: Date.now(),
    users,
    inbounds,
    user_inbounds: links,
    admins,
    settings,
  };
}

export function importData(
  payload: BackupPayload,
  options: { freshPaths?: boolean } = {},
): { users: number; inbounds: number; freshPaths: number } {
  if (!payload || (payload.version !== 1 && payload.version !== 2))
    throw new Error("invalid backup version");
  // 🧩 (وصلهٔ ما) شمارندهٔ مسیرهای تازه‌ساخته‌شده — بیرونِ تراکنش تعریف می‌شود
  let freshPaths = 0;
  // 🧩 (وصلهٔ ما) بکاپِ سبک (بدونِ کاربران) نباید مشتریانِ فعلیِ پنل را پاک کند:
  //    فقط اینباندها و تنظیمات عوض می‌شوند. پیوندِ کاربر↔اینباند با حذفِ
  //    اینباند آبشاری پاک می‌شود؛ پس اول نگهش می‌داریم و بعد دوباره وصل می‌کنیم.
  const withUsers = Array.isArray(payload.users) && payload.users.length > 0;
  let keepLinks: { user_id: number; inbound_id: number }[] = [];
  if (!withUsers) {
    try {
      keepLinks = db
        .prepare("SELECT user_id, inbound_id FROM user_inbounds")
        .all() as unknown as { user_id: number; inbound_id: number }[];
    } catch {
      keepLinks = [];
    }
  }
  // 🧩 (وصلهٔ ما) مسیرهای «زندهٔ» اینباندها را پیش از پاک‌کردن نگه می‌داریم؛
  //    ری‌استورِ بکاپِ سبک از آن استفاده می‌کند تا کانفیگِ کاربرانِ فعلی نشکند.
  const livePaths = new Map<number, string>();
  try {
    for (const r of db
      .prepare("SELECT id, path FROM inbounds")
      .all() as unknown as { id: number; path: string }[])
      livePaths.set(r.id, r.path);
  } catch {
    /* جدولِ تازه */
  }
  const tx = () => {
    if (withUsers)
      db.exec("DELETE FROM user_inbounds; DELETE FROM users; DELETE FROM inbounds;");
    else db.exec("DELETE FROM inbounds;");

    const insInbound = db.prepare(
      `INSERT INTO inbounds (id, tag, label, protocol, transport, port, path, host, enabled, created_at)
       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
    );
    for (const ib of payload.inbounds) {
      // 🧩 (وصلهٔ ما) قاعدهٔ مسیر در ری‌استور:
      //   • مسیرِ دوبخشی (بکاپ‌های کاملِ قدیمی): فقط با تیکِ «مسیرهای تازه» عوض می‌شود.
      //   • مسیرِ یک‌بخشی (خروجیِ بکاپِ سبک، مثل ‎/wpnfa‎): اگر پنل از قبل اینباندی با
      //     همین شناسه و همین پیشوند دارد، «همان مسیرِ زنده» می‌ماند تا کانفیگِ
      //     کاربرانِ فعلی نشکند؛ وگرنه (پنلِ خالی/تازه یا با تیکِ مسیرهای تازه)
      //     دمِ رندومِ تازه ساخته می‌شود.
      let path = ib.path;
      const seg = String(ib.path || "").split("/").filter(Boolean);
      const fresh = () => {
        path = "/" + seg[0] + "/" + (ib.transport || "ws") + "-" + nanoid(8);
        freshPaths++;
      };
      if (seg.length >= 2) {
        if (options.freshPaths) fresh();
      } else if (seg.length === 1) {
        const live = livePaths.get(ib.id) || "";
        const liveSeg = String(live).split("/").filter(Boolean);
        if (!options.freshPaths && liveSeg.length > 1 && liveSeg[0] === seg[0]) path = live;
        else fresh();
      }
      insInbound.run(
        ib.id,
        ib.tag,
        ib.label ?? "", // 🧩 نامِ اینباند (قبلاً جا می‌افتاد)
        ib.protocol,
        ib.transport,
        ib.port,
        path,
        ib.host,
        ib.enabled,
        ib.created_at,
      );
    }

    const insUser = db.prepare(
      `INSERT INTO users
        (id, email, uuid, password, sub_token, fingerprint, alpn, data_limit, ip_limit,
         expire_at, sub_expire_days, sub_first_seen, traffic_reset, telegram_id, comment,
         enabled, up, down, last_reset, online_at, created_by, created_at)
       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
    );
    for (const u of payload.users) {
      insUser.run(
        u.id,
        u.email,
        u.uuid,
        u.password,
        u.sub_token,
        u.fingerprint,
        u.alpn,
        u.data_limit,
        u.ip_limit,
        u.expire_at,
        u.sub_expire_days,
        u.sub_first_seen,
        u.traffic_reset,
        u.telegram_id,
        u.comment,
        u.enabled,
        u.up,
        u.down,
        u.last_reset,
        u.online_at,
        u.created_by ?? null,
        u.created_at,
      );
    }

    const insLink = db.prepare(
      "INSERT OR IGNORE INTO user_inbounds (user_id, inbound_id) VALUES (?, ?)",
    );
    for (const l of payload.user_inbounds) insLink.run(l.user_id, l.inbound_id);
    // 🧩 (وصلهٔ ما) بکاپِ سبک: کاربرانِ فعلی با همین شناسه‌های اینباند وصل می‌مانند
    if (!withUsers) for (const l of keepLinks) insLink.run(l.user_id, l.inbound_id);

    if (payload.admins && payload.admins.length > 0) {
      db.exec("DELETE FROM admins");
      const insAdmin = db.prepare(
        `INSERT INTO admins (id, username, password_hash, role, permissions, data_limit, created_at)
         VALUES (?, ?, ?, ?, ?, ?, ?)`,
      );
      for (const a of payload.admins) {
        insAdmin.run(
          a.id,
          a.username,
          a.password_hash,
          a.role || "admin",
          a.permissions || "[]",
          a.data_limit || 0,
          a.created_at,
        );
      }
    }

    if (payload.settings) {
      const insSetting = db.prepare(
        "INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
      );
      for (const s of payload.settings) insSetting.run(s.key, s.value);
    }
  };
  db.exec("BEGIN");
  try {
    tx();
    db.exec("COMMIT");
  } catch (e) {
    db.exec("ROLLBACK");
    throw e;
  }
  return {
    users: (payload.users || []).length,
    inbounds: (payload.inbounds || []).length,
    freshPaths,
  };
}
