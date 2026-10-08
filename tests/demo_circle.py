"""Slow visible cursor test: center pause, then slow circles."""
import math
import time

from opencode_computer_use import mouse

CX, CY, R = 960, 540, 300
STEPS = 150
DELAY = 0.04  # ~6 s per revolution

mouse.move_to(CX, CY)
print("centered - find the cursor, circle starts in 2 s", flush=True)
time.sleep(2.0)

for i in range(STEPS + 1):
    t = 2 * math.pi * i / STEPS
    mouse.move_to(int(CX + R * math.cos(t)), int(CY + R * math.sin(t)))
    time.sleep(DELAY)
print("clockwise done - reverse in 1.5 s", flush=True)
time.sleep(1.5)

for i in range(STEPS + 1):
    t = 2 * math.pi * (1 - i / STEPS)
    mouse.move_to(int(CX + R * math.cos(t)), int(CY + R * math.sin(t)))
    time.sleep(DELAY)
print("counterclockwise done", flush=True)
