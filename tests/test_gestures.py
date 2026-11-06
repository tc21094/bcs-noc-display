"""Gesture engine tests on synthetic hands: what should and shouldn't trigger. Run: python3 tests/test_gestures.py"""
import importlib.machinery, importlib.util, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from synth import hand

here = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_loader("bg", importlib.machinery.SourceFileLoader("bg", os.path.join(here, "..", "bin", "bcs-gesture")))
bg = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bg)
bg.log = lambda *a: None

FPS = 30
ok = True


USE_WORLD = os.environ.get("BCS_TEST_WORLD", "1") == "1"   # 3D finger check (as with the real tracker) or 2D only


def H(d, canned=None):
    return bg.Hand([tuple(p) for p in d["pts"]], d["handed"], 1.0,
                   [tuple(w) for w in d["world"]] if USE_WORLD and d.get("world") else None, canned)


def run(script, eng=None, t0=1000.0):
    """script: list of (seconds, fn(t) -> [hand dicts]). Returns (engine, states, events)."""
    if eng is not None:
        t0 = eng.last_t + 1 / FPS          # carry on from where the last script left off
    eng = eng or bg.Engine(0.045)
    t, states, events = t0, [], []
    for dur, fn in script:
        for i in range(int(dur * FPS)):
            st = eng.update([H(h) for h in fn(i / FPS)], t)
            for e in st["ev"]:
                if e[0] > getattr(eng, "_seen", 0):        # each event once, even across scripts
                    events.append(e)
                    eng._seen = e[0]
            states.append(st)
            t += 1 / FPS
    return eng, states, [n for _, n in events]


def check(name, cond, info=""):
    global ok
    print(("PASS " if cond else "FAIL ") + name + (f"   [{info}]" if info else ""))
    ok &= bool(cond)


# --- poses are recognised
for pose in ("open", "fist", "point", "victory", "pinch"):
    for handed in ("Right", "Left"):
        h = H(hand(pose, handed=handed))
        check(f"pose {pose} ({handed})", h.pose == pose, f"got {h.pose}")
from synth import foreshortened_open
if USE_WORLD:
    check("open hand tipped toward the camera is still open (3D)", H(foreshortened_open()).pose == "open", H(foreshortened_open()).pose)
check("trained classifier rescues an unclear hand", H(hand("other"), ("Open_Palm", 0.9)).pose == "open")
check("trained classifier ignored when unsure", H(hand("other"), ("Open_Palm", 0.4)).pose == "other")
check("a pinch stays a pinch whatever the classifier says", H(hand("pinch"), ("Closed_Fist", 0.9)).pose == "pinch")
check("one finger read as bent still counts as open", H(hand("open")).pose == "open" and bg.Hand([tuple(p) for p in hand("other")["pts"]], "Right").pose != "open")
h = H(hand("open"))
check("open palm is upright and facing", h.upright and h.facing)
check("back of hand is not facing", not H(hand("open", facing=False)).facing)
check("left palm facing", H(hand("open", handed="Left")).facing)

still = lambda **k: (lambda t: [hand(**k)])
nothing = lambda t: []

# --- things that must NOT wake it
_, _, ev = run([(3, lambda t: [hand("open", x=0.2 + 0.6 * t, palm=0.1)])])          # walking past, palm up
check("passer-by moving an open palm does not wake", "wake" not in ev, str(ev))
_, _, ev = run([(3, still(pose="open", palm=0.03))])                                  # far away
check("far-away palm does not wake", "wake" not in ev, str(ev))
_, _, ev = run([(3, still(pose="open", tilt=180))])                                   # arm hanging down
check("hand hanging down does not wake", "wake" not in ev, str(ev))
_, _, ev = run([(3, still(pose="open", tilt=75))])                                    # sideways
check("sideways hand does not wake", "wake" not in ev, str(ev))
_, _, ev = run([(3, still(pose="open", facing=False))])                               # back of the hand
check("back of the hand wakes too (palm-facing check off by default)", "wake" in ev, str(ev))
_, _, ev = run([(3, still(pose="open", facing=False))], bg.Engine(0.045, need_facing=True))
check("with facing=yes, the back of the hand does not wake", "wake" not in ev, str(ev))
_, _, ev = run([(3, still(pose="fist"))])
check("fist does not wake", "wake" not in ev, str(ev))
_, _, ev = run([(0.7, still(pose="open")), (0.5, nothing), (0.7, still(pose="open"))])
check("two short holds do not add up to a wake", "wake" not in ev, str(ev))

# --- wake, cursor
eng, st, ev = run([(1.3, still(pose="open", x=0.9, y=0.5, palm=0.1))])
check("held open palm wakes", ev == ["wake"] and st[-1]["on"], str(ev))
wake_at = next(i for i, s in enumerate(st) if s["on"]) / FPS
check("wake takes about a second", 0.95 <= wake_at <= 1.3, f"{wake_at:.2f} s")

# --- real-world noise: a small far hand jitters a few pixels a frame; the tracker drops a frame now and then
import random
random.seed(4)
_, _, ev = run([(2.0, lambda t: [hand("open", x=0.9 + random.uniform(-0.004, 0.004), y=0.5 + random.uniform(-0.004, 0.004), palm=0.05)])])
check("jittery far-away (but in range) hand still wakes", "wake" in ev, str(ev))
_, _, ev = run([(2.0, lambda t: [] if int(t * 30) in (12, 13, 22) else [hand("open", x=0.9, y=0.5)])])
check("a couple of dropped frames don't spoil the hold", "wake" in ev, str(ev))
check("hold progress is shown before waking", any(s["hold"] and s["hold"]["k"] == "wake" and 0.4 < s["hold"]["p"] < 1 for s in st))
check("cursor starts in the middle", abs(st[-1]["x"] - 0.5) < 0.02 and abs(st[-1]["y"] - 0.5) < 0.02)

# move right 1.25 palm lengths (= quarter screen) slowly, then hold
eng, st, ev = run([(1.0, lambda t: [hand("open", x=0.9 + 0.125 * t, y=0.5)]), (0.5, still(pose="open", x=1.025, y=0.5))], eng)
check("cursor follows the hand", abs(st[-1]["x"] - 0.75) < 0.03, f"x={st[-1]['x']}")
eng, st, ev = run([(1.0, lambda t: [hand("open", x=1.025, y=0.5 - 0.08 * t)]), (0.5, still(pose="open", x=1.025, y=0.42))], eng)
check("cursor moves up", abs(st[-1]["y"] - (0.5 - 0.08 / (3.2 * 0.1))) < 0.03, f"y={st[-1]['y']}")
jit = [s["x"] for s in run([(1.0, lambda t: [hand("open", x=1.025 + 0.0015 * ((int(t * 30) % 2) * 2 - 1), y=0.42)])], eng)[1]]
check("cursor is steady when the hand jitters", max(jit[10:]) - min(jit[10:]) < 0.004, f"spread {max(jit[10:]) - min(jit[10:]):.4f}")

# --- someone else's hand passing does not steal the cursor
xb = st[-1]["x"]
eng, st, ev = run([(1.0, lambda t: [hand("open", x=1.025, y=0.42), hand("open", x=0.2 + 0.4 * t, y=0.3, palm=0.13)])], eng)
check("a second hand passing does not move the cursor", abs(st[-1]["x"] - xb) < 0.02 and st[-1]["on"], f"x={st[-1]['x']}")

# --- pinch zoom
eng, st, ev = run([(0.3, still(pose="pinch", x=1.025, y=0.42)),
                   (1.0, lambda t: [hand("pinch", x=1.025, y=0.42 - 0.14 * t)]),
                   (0.3, still(pose="pinch", x=1.025, y=0.28))], eng)
check("pinch + raise zooms in ~2x", st[-1]["pinch"] and 1.8 < st[-1]["zf"] < 2.3, f"zf={st[-1]['zf']}")
xs = [s["x"] for s in st]
check("cursor holds still while zooming", max(xs) - min(xs) < 0.02, f"{min(xs):.3f}-{max(xs):.3f}")
eng, st, ev = run([(0.4, still(pose="open", x=1.025, y=0.28))], eng)
check("releasing the pinch ends the zoom, cursor doesn't jump", not st[-1]["pinch"] and abs(st[-1]["x"] - xs[-1]) < 0.02)

# --- swipe
before = st[-1]["x"], st[-1]["y"]
eng, st, ev = run([(0.25, lambda t: [hand("open", x=1.025 - 1.1 * t, y=0.3)]), (0.6, still(pose="open", x=0.75, y=0.3))], eng)
check("quick swipe left = next", ev.count("next") == 1 and "prev" not in ev, str(ev))
check("cursor stays where it was through the swipe", abs(st[-1]["x"] - before[0]) < 0.06, f"{st[-1]['x']} vs {before[0]}")
eng, st, ev = run([(0.8, still(pose="open", x=0.75, y=0.3)), (0.25, lambda t: [hand("open", x=0.75 + 1.1 * t, y=0.3)]), (0.6, still(pose="open", x=1.03, y=0.3))], eng)
check("quick swipe right = previous", ev.count("prev") == 1 and "next" not in ev, str(ev))
eng, st, ev = run([(2.0, lambda t: [hand("open", x=1.03 - 0.15 * t, y=0.3)])], eng)
check("slow sideways move is not a swipe", "next" not in ev and "prev" not in ev, str(ev))

# --- holds
eng, st, ev = run([(1.6, still(pose="fist", x=0.73, y=0.3))], eng)
check("fist held = pause rotation", ev.count("pause") == 1, str(ev))
eng, st, ev = run([(0.5, still(pose="open", x=0.73, y=0.3)), (2.0, still(pose="victory", x=0.73, y=0.3))], eng)
check("V held = interlude", ev.count("interlude") == 1, str(ev))
eng, st, ev = run([(0.5, still(pose="open", x=0.73, y=0.3)), (0.6, still(pose="fist", x=0.73, y=0.3)), (0.6, still(pose="open", x=0.73, y=0.3))], eng)
check("a quick fist does nothing", "pause" not in ev, str(ev))

# --- click: a quick pinch and let go
eng, st, ev = run([(0.5, still(pose="open", x=0.73, y=0.3)), (0.2, still(pose="pinch", x=0.73, y=0.3)), (0.5, still(pose="open", x=0.73, y=0.3))], eng)
check("quick pinch = click", ev.count("click") == 1, str(ev))
check("no zoom from a click", all(abs(s_["zf"] - 1) < 0.05 for s_ in st if s_["pinch"]), max(s_["zf"] for s_ in st if s_["pinch"]))
eng, st, ev = run([(0.4, still(pose="pinch", x=0.73, y=0.3)), (0.8, lambda t: [hand("pinch", x=0.73, y=0.3 - 0.1 * t)]), (0.5, still(pose="open", x=0.73, y=0.2))], eng)
check("pinch and raise zooms, no click", "click" not in ev, str(ev))
eng, st, ev = run([(1.2, still(pose="pinch", x=0.73, y=0.2)), (0.5, still(pose="open", x=0.73, y=0.2))], eng)
check("a long pinch held still is not a click", "click" not in ev, str(ev))

# --- drawing: hold a pointing finger still
eng, st, ev = run([(1.0, still(pose="point", x=0.73, y=0.2))], eng)
check("a pointing finger held briefly doesn't start drawing", "draw_on" not in ev and not st[-1]["draw"], str(ev))
check("...but shows the draw ring filling", any(s_["hold"] and s_["hold"]["k"] == "draw" for s_ in st))
eng, st, ev = run([(1.0, still(pose="point", x=0.73, y=0.2))], eng)
check("held still ~1.5 s: drawing on", "draw_on" in ev and st[-1]["draw"], str(ev))
eng, st, ev = run([(1.0, lambda t: [hand("point", x=0.73 + 0.1 * t, y=0.2 + 0.05 * t)])], eng)
check("pointing draws (pen down) and moves the cursor", all(s_["pen"] for s_ in st[3:]) and st[-1]["x"] > st[0]["x"], st[-1]["x"])
eng, st, ev = run([(0.6, lambda t: [hand("open", x=0.83 + 0.05 * t, y=0.25)])], eng)
check("open hand lifts the pen", not st[-1]["pen"] and st[-1]["draw"])
eng, st, ev = run([(0.3, lambda t: [hand("open", x=0.88 - 1.0 * t, y=0.25)]), (0.4, still(pose="open", x=0.58, y=0.25))], eng)
check("no dashboard flicks while drawing", "next" not in ev and "prev" not in ev, str(ev))
eng, st, ev = run([(0.3, still(pose="pinch", x=0.58, y=0.25)), (0.3, still(pose="open", x=0.58, y=0.25))], eng)
check("no clicks or zoom while drawing", "click" not in ev and not any(s_["pinch"] for s_ in st), str(ev))
eng, st, ev = run([(1.6, still(pose="fist", x=0.58, y=0.25))], eng)
check("fist held while drawing = clear and stop drawing (not pause)", "draw_off" in ev and "pause" not in ev and not st[-1]["draw"], str(ev))
eng, st, ev = run([(1.0, lambda t: [hand("open", x=0.58 + 0.02 * t, y=0.25)]), (1.0, lambda t: [hand("point", x=0.6 + 0.1 * t, y=0.25)])], eng)
check("hovering with an open hand, or moving a pointing finger, doesn't start drawing", "draw_on" not in ev, str(ev))
eng, st, ev = run([(3.0, lambda t: [hand("point", x=0.6 + 0.05 * t, y=0.25 + 0.02 * t)])], eng)
check("slowly pointing at things for a while doesn't start drawing", "draw_on" not in ev, str(ev))

# --- going away
eng, st, ev = run([(3.5, nothing)], eng)
check("cursor goes away when the hand leaves", "sleep" in ev and not st[-1]["on"], str(ev))
eng2, st, ev = run([(1.0, still(pose="open")), (0.5, nothing), (1.0, still(pose="open"))])
check("nothing happens without waking first", ev == [], str(ev))

# --- blanket: both palms
_, st, ev = run([(2.0, lambda t: [hand("open", x=0.6, palm=0.1), hand("open", x=1.2, palm=0.1, handed="Left")])])
check("both palms held = blanket", ev.count("blanket") == 1 and "wake" not in ev, str(ev))
check("blanket hold shows progress", any(s["hold"] and s["hold"]["k"] == "blanket" for s in st))
_, st, ev = run([(2.0, lambda t: [hand("open", x=0.6 + 0.3 * t, palm=0.1), hand("open", x=1.2 + 0.3 * t, palm=0.1, handed="Left")])])
check("two palms moving do not toggle the blanket", "blanket" not in ev, str(ev))
_, st, ev = run([(2.0, lambda t: [hand("open", x=0.6, palm=0.1), hand("open", x=1.2, palm=0.03, handed="Left")])])
check("one near + one far palm is not the blanket gesture", "blanket" not in ev, str(ev))

# --- one camera, three displays: the cursor starts on the camera's display and sweeps across
eng = bg.Engine(0.045, wall=(2, 3))
eng, st, ev = run([(1.3, still(pose="open", x=0.9, y=0.5))], eng)
check("on a 3-display wall the cursor starts on the camera's (middle) display", st[-1]["on"] and abs(st[-1]["x"] - 1.5) < 0.02, f"x={st[-1]['x']}")
eng, st, ev = run([(0.4, lambda t: [hand("point", x=0.9 + 0.75 * t, y=0.5)]), (0.4, still(pose="point", x=1.2, y=0.5))], eng)
check("a quick sweep right reaches the right-hand display", st[-1]["x"] > 2.0 and "next" not in ev and "prev" not in ev, f"x={st[-1]['x']} {ev}")
x_r = st[-1]["x"]
eng, st, ev = run([(1.0, lambda t: [hand("point", x=1.2 - 0.05 * t, y=0.5)]), (0.3, still(pose="point", x=1.15, y=0.5))], eng)
check("slow moves stay precise (no speed-up)", abs((x_r - st[-1]["x"]) - 0.05 / 0.1 / 5) < 0.03, f"moved {x_r - st[-1]['x']:.3f}")
eng, st, ev = run([(1.2, lambda t: [hand("point", x=1.15 - 0.6 * t, y=0.5)]), (0.3, still(pose="point", x=0.43, y=0.5))], eng)
check("a sweep left reaches the left-hand display", st[-1]["x"] < 1.0, f"x={st[-1]['x']}")
check("cursor never leaves the wall", all(0 <= s_["x"] < 3 for s_ in st))

print("\nALL PASS" if ok else "\nSOME FAILED")
sys.exit(0 if ok else 1)
