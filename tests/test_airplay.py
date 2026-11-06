"""AirPlay wall maths: picture sizes per setting, and each TV's slice. Run: python3 tests/test_airplay.py"""
import importlib.machinery, importlib.util, os, sys, types
here = os.path.dirname(os.path.abspath(__file__))


def load(name):
    spec = importlib.util.spec_from_loader(name, importlib.machinery.SourceFileLoader(name, os.path.join(here, "..", "bin", name)))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


# bcs-wallplayer imports GStreamer; the slice maths doesn't need it
gi = types.ModuleType("gi"); gi.require_version = lambda *a: None
repo = types.ModuleType("gi.repository"); repo.Gst = repo.GLib = None
sys.modules.update({"gi": gi, "gi.repository": repo})
ap, wp = load("bcs-airplay"), load("bcs-wallplayer")
ok = True


def check(name, cond, info=""):
    global ok
    print(("PASS " if cond else "FAIL ") + name + (f"   [{info}]" if info else ""))
    ok &= bool(cond)


w, h, h265 = ap.size("wall", "720", 3, 0.08)
check("wall 720 on 3 TVs: one 1280x720 slice per TV plus two bezel gaps, H.264", (w, h, h265) == (4044, 720, False), (w, h, h265))
check("wall 540 is lighter, still H.264", ap.size("wall", "540", 3, 0.08)[2] is False and ap.size("wall", "540", 3, 0.08)[1] == 540)
check("wall 1080 needs H.265 (wider than 4096)", ap.size("wall", "1080", 3, 0.08)[2] is True)
check("center 1080 is plain 1080p H.264", ap.size("center", "1080", 3, 0.08) == (1920, 1080, False))
check("center 2160 is 4K H.265", ap.size("center", "2160", 3, 0.08) == (3840, 2160, True))
slices = [wp.slice_of(4044, 720, p, 3, 0.08) for p in (1, 2, 3)]
starts = [l for l, r, t, b in slices]
widths = [4044 - l - r for l, r, t, b in slices]
check("three slices left to right", starts[0] == 0 and starts[0] < starts[1] < starts[2], starts)
check("each slice is one TV wide (16:9)", all(abs(x - 1280) <= 2 for x in widths), widths)
check("the bezel gap between slices is skipped", abs((starts[1] - (starts[0] + widths[0])) - 0.08 * 1280) <= 2, starts[1] - widths[0])
check("the last slice ends at the right edge", abs(starts[2] + widths[2] - 4044) <= 2)
print("\nALL PASS" if ok else "\nSOME FAILED")
sys.exit(0 if ok else 1)
