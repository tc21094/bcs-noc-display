"""Room-aware dimming: movement detection on synthetic camera pictures. Run with the gesture venv's python
(it needs numpy):  /opt/bcs-noc/gesture/bin/python tests/test_motion.py"""
import importlib.machinery, importlib.util, os, sys
import numpy as np
here = os.path.dirname(os.path.abspath(__file__))
sp = importlib.util.spec_from_loader("bg", importlib.machinery.SourceFileLoader("bg", os.path.join(here, "..", "bin", "bcs-gesture")))
bg = importlib.util.module_from_spec(sp); sp.loader.exec_module(bg)
rng = np.random.default_rng(1)
room = (rng.random((36, 64)) * 60 + 70).astype("float32")
ok = True


def noise(a=3, base=None):
    return (room if base is None else base) + rng.normal(0, a, room.shape).astype("float32")


def run(frames, sens="normal"):
    m, t = bg.Motion(sens), 1000.0
    for f in frames:
        m.check(np.clip(f, 0, 255).astype("float32"), t)
        t += 0.5
    return m


def check(name, cond):
    global ok
    print(("PASS " if cond else "FAIL ") + name)
    ok &= bool(cond)


check("empty room with camera grain: nobody", not run([noise() for _ in range(60)]).last)
check("dark grainy room: nobody", not run([noise(8, room * 0.2) for _ in range(60)]).last)
check("the TVs dim (the whole room darkens): nobody", not run([noise() * (1 - 0.45 * min(1, i / 6)) for i in range(40)]).last)


def uneven(i):
    f = noise()
    f[:, 32:] *= (1 - 0.35 * min(1, i / 6))
    return f


check("half the room darkens: nobody", not run([uneven(i) for i in range(40)]).last)
yy, xx = np.mgrid[0:36, 0:64]
check("a smooth glow fades (light from the TVs): nobody",
      not run([noise() * (1 - 0.4 * min(1, i / 6) * (xx / 64.0)) for i in range(40)]).last)
check("the camera's exposure creeps: nobody", not run([noise() * (1 + 0.02 * i) for i in range(30)]).last)


def walk(i):
    f = noise()
    x = int(i * 2.5) % 60
    f[8:36, x:x + 6] = 25
    return f


check("someone walks through: seen", bool(run([walk(i) for i in range(20)]).last))


def walk_dark(i):
    f = noise(6, room * 0.25)
    x = int(i * 2.5) % 60
    f[8:36, x:x + 6] = 4
    return f


check("someone walks through a dark room: seen", bool(run([walk_dark(i) for i in range(20)]).last))


def wave(i):
    f = noise()
    y = 12 + int(4 * np.sin(i * 1.3))
    f[y:y + 5, 40:45] = 230
    return f


check("someone at a desk waving a hand: seen", bool(run([wave(i) for i in range(20)]).last))
print("\nALL PASS" if ok else "\nSOME FAILED")
sys.exit(0 if ok else 1)
