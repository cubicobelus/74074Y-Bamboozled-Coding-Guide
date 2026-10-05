# PID Tuning Log

> Markdown mirror for readable GitHub viewing. Print the `.docx` version, or copy this into a notebook, and fill in one row per test.

The reason this sheet exists: tuning is easy to do badly. Change two numbers at once and you will never know which one helped. Change one number, write down what happened, repeat — and you will be done in twenty minutes instead of an afternoon.

**Robot:** _______________________ **Date:** ______________ **Surface:** carpet / foam tiles / other: __________

**Wheel diameter:** __________ in **Gear ratio:** __________ (motor teeth ÷ wheel teeth)

## Part 1 — drive_distance

Test the same move every time. 24 inches is a good one — it's exactly one field tile.

| # | DRIVE_kP | DRIVE_kD | Asked for | Actually went | Overshoot? Bounce? | Keep it? |
| --- | --- | --- | --- | --- | --- | --- |
| 1 |  |  | 24 in |  |  |  |
| 2 |  |  | 24 in |  |  |  |
| 3 |  |  | 24 in |  |  |  |
| 4 |  |  | 24 in |  |  |  |
| 5 |  |  | 24 in |  |  |  |
| 6 |  |  | 24 in |  |  |  |

**Reminders**

- Stops short → raise kP
- Overshoots → raise kD
- Rocks back and forth → lower kP
- Wrong by a *percentage* at every distance → this is not tuning. Recheck wheel diameter and gear ratio.

**Final values:** DRIVE_kP = __________ DRIVE_kD = __________

## Part 2 — turn_to_angle

Test a 90-degree turn every time.

| # | TURN_kP | TURN_kD | Asked for | Ended at | Overshoot? Shake? | Keep it? |
| --- | --- | --- | --- | --- | --- | --- |
| 1 |  |  | 90° |  |  |  |
| 2 |  |  | 90° |  |  |  |
| 3 |  |  | 90° |  |  |  |
| 4 |  |  | 90° |  |  |  |
| 5 |  |  | 90° |  |  |  |
| 6 |  |  | 90° |  |  |  |

**Reminders**

- Stops short of the angle → raise kP
- Overshoots and swings back → raise kD
- Shakes at the end → lower kP

**Final values:** TURN_kP = __________ TURN_kD = __________

## Part 3 — Driving straight

Run a 24-inch drive and watch the robot from directly behind it.

| # | DRIVE_HEADING_kP | Drifted left / right / straight | Snaked? | Keep it? |
| --- | --- | --- | --- | --- |
| 1 |  |  |  |  |
| 2 |  |  |  |  |
| 3 |  |  |  |  |
| 4 |  |  |  |  |

- Still drifts to one side → **raise** it
- Snakes back and forth → **lower** it

**Final value:** DRIVE_HEADING_kP = __________

## Part 4 — The square test

Select route 3. Put tape at one corner of the robot. Run it. The robot should come back to the tape facing the same way.

| Attempt | Ended how far from the tape? | Ended how many degrees off? | What that means |
| --- | --- | --- | --- |
| 1 |  |  |  |
| 2 |  |  |  |
| 3 |  |  |  |

**Reading the result**

| Result | Go back to |
| --- | --- |
| Short or long of the tape, but square | Part 1 — distance |
| On the tape, but rotated | Part 2 — turns |
| Drifted sideways into a parallelogram | Part 3 — heading correction |
| On the tape, facing forward | Nothing. You're done. |

## Notes

Anything weird you noticed, mechanical problems you found, things to try next time:

---
