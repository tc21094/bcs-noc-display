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
mkdir -p build/payload/share
python3 - <<'PY2'
import base64, json
js = open("interlude.js.in").read()
data = open("interlude_data.json").read()
b64 = lambda f: base64.b64encode(open(f, "rb").read()).decode()
for k, v in {"@@DATA@@": data, "@@LOGO@@": b64("theme/x2/logo.png"),
             "@@GLOW@@": b64("theme/x2/logo_glow.png"), "@@TEXT@@": b64("theme/x2/text.png"),
             "@@TEXT2@@": b64("theme/x2/text_dept.png")}.items():
    assert js.count(k) == 1, k
    js = js.replace(k, v)
open("build/payload/share/interlude.js", "w").write(js)
PY2
tar -C build/payload --owner=0 --group=0 -czf build/payload.tgz theme wallpaper.jpg bin share
base64 -w 76 build/payload.tgz > build/payload.b64
python3 - <<'PY'
src = open("install.sh.in").read()
payload = open("build/payload.b64").read().rstrip("\n")
assert src.count("@@PAYLOAD@@") == 1
open("../install.sh", "w").write(src.replace("@@PAYLOAD@@", payload))
PY
chmod +x ../install.sh
rm -rf build theme build_wallpaper.png trace_data.script interlude_data.json preview_static.png preview_blanket.png wallpaper.jpg
ls -la ../install.sh
