#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────────────────────
#  sync_panel.py — آینه‌کردنِ پوشهٔ پنل در ریپوی GitHub (یک مرجعِ یکتا)
#  فقط فایل‌های تغییرکرده فرستاده می‌شوند (مقایسهٔ blob-sha)، در یک کامیت.
#  استفاده:  python3 dev/sync_panel.py [پیامِ کامیت]
#  توکن:     GH_TOKEN از محیط یا /home/user/tokens.env
# ─────────────────────────────────────────────────────────────────────────────
import hashlib, json, os, sys, urllib.error, urllib.request

REPO = "baddarksss/siderail-panel"
BRANCH = "main"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKIP_DIRS = {"node_modules", ".git", "dist", "build", ".next", "coverage", "out",
             ".turbo", ".cache", ".venv", "__pycache__", ".svelte-kit", "data"}
SKIP_FILES = {".DS_Store", "tsconfig.app.tsbuildinfo", "tsconfig.node.tsbuildinfo", "tsconfig.tsbuildinfo"}


def load_token():
    if os.environ.get("GH_TOKEN"):
        return os.environ["GH_TOKEN"]
    for line in open("/home/user/tokens.env", encoding="utf-8"):
        if line.startswith("GH_TOKEN="):
            return line.split("=", 1)[1].strip()
    sys.exit("❌ GH_TOKEN پیدا نشد")


GH = load_token()


def api(method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request("https://api.github.com" + path, data=data, method=method,
                               headers={"Authorization": "Bearer " + GH,
                                        "Accept": "application/vnd.github+json",
                                        "User-Agent": "arena-agent"})
    try:
        with urllib.request.urlopen(r, timeout=120) as resp:
            return resp.status, json.loads(resp.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        return e.code, e.read()[:300].decode()


def blob_sha(b: bytes) -> str:
    return hashlib.sha1(b"blob %d\x00" % len(b) + b).hexdigest()


def local_files():
    out = {}
    for dp, dns, fns in os.walk(ROOT):
        dns[:] = [d for d in dns if d not in SKIP_DIRS]
        for fn in fns:
            if fn in SKIP_FILES:
                continue
            p = os.path.join(dp, fn)
            rel = os.path.relpath(p, ROOT).replace(os.sep, "/")
            out[rel] = p
    return out


def main():
    msg = sys.argv[1] if len(sys.argv) > 1 else "sync panel"
    st, ref = api("GET", f"/repos/{REPO}/git/ref/heads/{BRANCH}")
    if st != 200:
        sys.exit(f"❌ خواندنِ شاخه: {st} {ref}")
    head = ref["object"]["sha"]
    _, commit = api("GET", f"/repos/{REPO}/git/commits/{head}")
    base_tree = commit["tree"]["sha"]
    _, tree = api("GET", f"/repos/{REPO}/git/trees/{base_tree}?recursive=1")
    remote = {t["path"]: t["sha"] for t in tree.get("tree", []) if t["type"] == "blob"}

    files = local_files()
    changed, entries = [], []
    for rel, path in sorted(files.items()):
        b = open(path, "rb").read()
        sha = blob_sha(b)
        if remote.get(rel) == sha:
            continue
        st, res = api("POST", f"/repos/{REPO}/git/blobs",
                      {"content": b.decode("utf-8", "surrogateescape") if _is_text(b) else __import__("base64").b64encode(b).decode(),
                       "encoding": "utf-8" if _is_text(b) else "base64"})
        if st not in (200, 201):
            sys.exit(f"❌ blob {rel}: {st} {res}")
        entries.append({"path": rel, "mode": "100644", "type": "blob", "sha": res["sha"]})
        changed.append(rel)

    missing = [p for p in remote if p not in files and not p.startswith(".")]
    if not changed and not missing:
        print("✅ همه‌چیز به‌روز است — چیزی برای فرستادن نبود")
        return
    st, new_tree = api("POST", f"/repos/{REPO}/git/trees", {"base_tree": base_tree, "tree": entries})
    if st not in (200, 201):
        sys.exit(f"❌ tree: {st} {new_tree}")
    st, new_commit = api("POST", f"/repos/{REPO}/git/commits",
                         {"message": msg, "tree": new_tree["sha"], "parents": [head]})
    if st not in (200, 201):
        sys.exit(f"❌ commit: {st} {new_commit}")
    st, res = api("PATCH", f"/repos/{REPO}/git/refs/heads/{BRANCH}", {"sha": new_commit["sha"]})
    if st not in (200, 201):
        sys.exit(f"❌ ref: {st} {res}")
    print(f"✅ {len(changed)} فایل فرستاده شد ⇒ کامیت {new_commit['sha'][:10]} روی {BRANCH}")
    for c in changed:
        print("   •", c)
    if missing:
        print("ℹ️ در ریپو هست ولی محلی نیست (حذف نشد):", ", ".join(missing[:8]))


def _is_text(b: bytes) -> bool:
    try:
        b.decode("utf-8")
        return True
    except UnicodeDecodeError:
        return False


if __name__ == "__main__":
    main()
