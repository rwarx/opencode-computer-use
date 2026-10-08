"""Live check of annotated screenshot on the foreground window."""
import io


def log(*a):
    print(" ".join(str(x) for x in a).encode("ascii", "replace").decode(),
          flush=True)


from opencode_computer_use import annotate, capture, monitors, windows_mgr

a = windows_mgr.get_active_window()
log("active:", (a["process"] if a else None), (a["title"][:40] if a else None))
mons = monitors.list_monitors()
m1 = next(m for m in mons if m.id == 1)
cap = capture.capture_monitor(m1, scale=1.0)
marks = annotate.collect_marks(bounds=(m1.x, m1.y, m1.width, m1.height))
log("marks:", len(marks))
for m in marks[:20]:
    log(m["id"], m["control_type"], m["cx"], m["cy"])
png, sc, mm = annotate.annotate_capture(cap, marks)
open(r"C:\Users\NoName\Desktop\opencode-mcp\ann_test.png", "wb").write(png)
log("annotated ok scale:", round(sc, 3))
