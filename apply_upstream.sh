#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
#  آخرین سورسِ icubaby/SideRail را می‌گیرد، وصله‌های ما را رویش اعمال می‌کند.
#  استفاده:  ./apply_upstream.sh
# ─────────────────────────────────────────────────────────────────────────────
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
CHECK=""
[ "$1" = "--check" ] && CHECK=1
TMP="$(mktemp -d)"
BRANCH="${UPSTREAM_BRANCH:-main}"
echo "⬇️  دریافتِ upstream ($BRANCH)…"
curl -sL "https://codeload.github.com/icubaby/SideRail/tar.gz/refs/heads/$BRANCH" -o "$TMP/up.tgz"
tar xzf "$TMP/up.tgz" -C "$TMP"
SRC="$(ls -d "$TMP"/SideRail-* | head -1)"
if [ -n "$CHECK" ]; then
  echo "🔎 حالتِ بررسی: وصله‌ها روی سورسِ تازهٔ upstream آزموده می‌شوند (بدونِ تغییرِ ریپو)"
  cp -a "$SRC/apps" "$TMP/apps"
  mkdir -p "$TMP/patches" && cp "$HERE/patches/panel-patch.py" "$TMP/patches/"
  python3 "$TMP/patches/panel-patch.py" --root "$TMP"
  echo "✅ وصله‌ها روی نسخهٔ تازهٔ upstream بی‌ایراد اعمال شدند"
  rm -rf "$TMP"; exit 0
fi

# فقط کدِ اپلیکیشن را جای‌گزین می‌کنیم؛ اسناد/وصله‌های خودمان می‌مانند
rm -rf "$HERE/apps" "$HERE/Dockerfile" "$HERE/package.json" "$HERE/package-lock.json" \
       "$HERE/railway.json" "$HERE/railway.toml" "$HERE/railway-template.json" \
       "$HERE/.dockerignore" "$HERE/.gitignore" "$HERE/.gitattributes" "$HERE/.github" \
       "$HERE/LICENSE" "$HERE/NOTICE"
cp -a "$SRC/apps" "$HERE/apps"
for f in Dockerfile package.json package-lock.json railway.json railway.toml railway-template.json \
         .dockerignore .gitignore .gitattributes .github LICENSE NOTICE; do
  [ -e "$SRC/$f" ] && cp -a "$SRC/$f" "$HERE/$f"
done
echo "🩹 اعمالِ وصله‌ها…"
python3 "$HERE/patches/panel-patch.py" --root "$HERE"
echo "✅ آماده — حالا: npm ci && npm run typecheck && npm run build (اختیاری) و بعد commit/push"
