"""TV schedule rules (bcs-tv). Run: python3 tests/test_tv.py"""
import importlib.machinery, importlib.util, os, sys, time
here = os.path.dirname(os.path.abspath(__file__))
sp = importlib.util.spec_from_loader("tv", importlib.machinery.SourceFileLoader("tv", os.path.join(here, "..", "bin", "bcs-tv")))
tv = importlib.util.module_from_spec(sp); sp.loader.exec_module(tv)
ok = True


def check(name, cond, info=""):
    global ok
    print(("PASS " if cond else "FAIL ") + name + (f"   [{info}]" if info else ""))
    ok &= bool(cond)


def at(s):
    return time.mktime(time.strptime(s, "%Y-%m-%d %H:%M"))      # 2026-11-09 is a Monday


e = tv.parse_schedule("Mon-Fri 06:30-18:00, Sat 08:00-12:00, Fri 22:00-02:00")
for when, want in [("2026-11-09 06:29", False), ("2026-11-09 06:30", True), ("2026-11-09 17:59", True), ("2026-11-09 18:00", False),
                   ("2026-11-14 09:00", True), ("2026-11-14 12:00", False), ("2026-11-15 10:00", False),
                   ("2026-11-13 23:00", True), ("2026-11-14 01:30", True), ("2026-11-14 02:00", False)]:
    check(f"{when} {'on' if want else 'off'}", tv.scheduled_on(e, at(when)) == want)
t, on = tv.next_change(e, at("2026-11-09 17:00"))
check("next switch from Monday 5 PM: off at 6 PM", on is False and time.strftime("%a %H:%M", time.localtime(t)) == "Mon 18:00")
t, on = tv.next_change(e, at("2026-11-14 13:00"))
check("next switch from Saturday 1 PM: on Monday 6:30", on is True and time.strftime("%a %H:%M", time.localtime(t)) == "Mon 06:30")
for text, start, end in [("weekdays 6am-6pm", 360, 1080), ("Mon-Fri 8-5", 480, 1020), ("Monday-Friday 7:00 to 17:30", 420, 1050),
                         ("daily 0:00-24:00", 0, 1440), ("Fri 22-2", 1320, 120)]:
    r = tv.parse_schedule(text)
    check(f"'{text}' reads as {start // 60}:{start % 60:02d}-{end // 60}:{end % 60:02d}", r and r[0][1] == start and r[0][2] == end, str(r))
check("'Mon,Wed,Fri' days", tv.parse_schedule("Mon,Wed,Fri 08:00-17:00")[0][0] == {0, 2, 4})
check("'weekends' days", tv.parse_schedule("weekends 9-1")[0][0] == {5, 6})
check("'off' = no schedule", tv.parse_schedule("off") == [] and tv.scheduled_on([], at("2026-11-15 03:00")))
for bad in ["Mon-Fri", "Mon-Fri 25:00-26:00", "Blursday 8-5", "mon-fri 8-17 tuesday", "8-5"]:
    try:
        tv.parse_schedule(bad)
        check(f"'{bad}' is rejected", False)
    except ValueError:
        check(f"'{bad}' is rejected", True)
print("\nALL PASS" if ok else "\nSOME FAILED")
sys.exit(0 if ok else 1)
