#!/usr/bin/env bash
# Rebuild ../install.sh: boot theme + 4K wallpaper + control scripts, embedded in one file.
# usage: ./make_installer.sh [logo.png] [Orbitron.ttf]
set -e
cd "$(dirname "$0")"
LOGO="${1:-logo.png}"; FONT="${2:-Orbitron.ttf}"
./assemble.sh "$LOGO" "$FONT"
python3 wallpaper_4k.py "$LOGO" "$FONT" build_wallpaper.png --pulses
python3 -c "from PIL import Image; Image.open('build_wallpaper.png').save('wallpaper.jpg', quality=92, subsampling=0, optimize=True)"
rm -rf build && mkdir -p build/payload
cp -r theme build/payload/theme
cp wallpaper.jpg build/payload/
cp -r ../bin build/payload/bin
tar -C build/payload --owner=0 --group=0 -czf build/payload.tgz theme wallpaper.jpg bin
base64 -w 76 build/payload.tgz > build/payload.b64
python3 - <<'PY'
src = open("install.sh.in").read()
payload = open("build/payload.b64").read().rstrip("\n")
assert src.count("@@PAYLOAD@@") == 1
open("../install.sh", "w").write(src.replace("@@PAYLOAD@@", payload))
PY
chmod +x ../install.sh
rm -rf build theme build_wallpaper.png trace_data.script preview_static.png wallpaper.jpg
ls -la ../install.sh
