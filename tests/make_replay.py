"""Write a synthetic gesture session (jsonl) for 'bcs-gesture --replay'. Usage: make_replay.py OUT [blanket]"""
import json, sys, os
sys.path.insert(0, os.path.dirname(__file__))
from synth import hand

FPS = 30
frames, t = [], 0.0


def seg(dur, fn):
    global t
    n = int(dur * FPS)
    for i in range(n):
        frames.append({"t": round(t, 4), "hands": fn(i / FPS, i / max(1, n - 1))})
        t += 1 / FPS


X0, Y0 = 0.89, 0.5
TX, TY = X0 - 0.125 * 0.98, Y0 - 0.064 * 1.25           # ~ cursor (0.255, 0.25): over SW-01
if len(sys.argv) > 2 and sys.argv[2] == "blanket":
    seg(2.2, lambda s, u: [hand("open", x=0.6), hand("open", x=1.2, handed="Left")])
    seg(1.0, lambda s, u: [])
else:
    seg(1.5, lambda s, u: [hand("open", x=X0, y=Y0)])                                    # wake
    seg(1.5, lambda s, u: [hand("point", x=X0 + (TX - X0) * u, y=Y0 + (TY - Y0) * u)])   # move to SW-01
    seg(1.5, lambda s, u: [hand("point", x=TX, y=TY)])                                    # hover
    seg(0.4, lambda s, u: [hand("pinch", x=TX, y=TY)])
    seg(1.0, lambda s, u: [hand("pinch", x=TX, y=TY - 0.14 * u)])                         # zoom 2x
    seg(0.5, lambda s, u: [hand("pinch", x=TX, y=TY - 0.14)])
    seg(1.5, lambda s, u: [hand("point", x=TX, y=TY - 0.14)])                             # let go, look
    seg(0.25, lambda s, u: [hand("open", x=TX - 0.27 * u, y=TY - 0.14)])                  # swipe -> next
    seg(1.5, lambda s, u: [hand("open", x=TX - 0.27, y=TY - 0.14)])
    seg(1.7, lambda s, u: [hand("fist", x=TX - 0.27, y=TY - 0.14)])                       # pause
    seg(1.0, lambda s, u: [hand("point", x=TX - 0.27, y=TY - 0.14)])
    seg(4.0, lambda s, u: [])                                                             # walk away
with open(sys.argv[1], "w") as f:
    for fr in frames:
        f.write(json.dumps(fr) + "\n")
print(f"{len(frames)} frames, {t:.1f} s")
