#!/usr/bin/env bash
# Build dist/install.sh: rebuild theme assets, then embed them in the installer.
set -e
cd "$(dirname "$0")"
./assemble.sh "$1" "$2"
mkdir -p dist build
rm -rf build/payload && mkdir -p build/payload
cp -r theme build/payload/theme
cp wallpaper.jpg build/payload/
tar -C build/payload --owner=0 --group=0 -czf build/payload.tgz theme wallpaper.jpg
base64 -w 76 build/payload.tgz > build/payload.b64
python3 - <<'PY'
src = open("install.sh.in").read()
payload = open("build/payload.b64").read().rstrip("\n")
assert src.count("@@PAYLOAD@@") == 1
open("dist/install.sh", "w").write(src.replace("@@PAYLOAD@@", payload))
PY
chmod +x dist/install.sh
ls -la dist/install.sh
