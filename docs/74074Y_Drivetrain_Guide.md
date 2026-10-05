# VEX V5 PID Drivetrain Programming Guide

**Team:** 74074Y Bamboozled
**Language:** C++ (VEXcode V5)
**Companion file:** [`74074Y_Drivetrain_Template.cpp`](../template/74074Y_Drivetrain_Template.cpp)

> This is a Markdown mirror of the guide, kept here so it's readable directly
> on GitHub (with a clickable heading outline via the outline icon in the
> top-right of the file view). The version students actually read day-to-day
> is the Google Doc — see the link in the repo README — and the `.docx` file
> in this folder is what gets uploaded there.

## Welcome

If you have used VEX Blocks or Python before, C++ is going to look a little scary at first. It is not. It is the same ideas with more brackets. By the end of this guide your robot will drive itself a measured number of inches, turn to a compass heading, and hold a straight line while it does it — and you will understand why each line of code is there.

Everything here is built around two functions:

- `drive_distance(inches)` — move forward or backward a precise distance.
- `turn_to_angle(degrees)` — turn to face a specific direction.

Every autonomous routine you will ever write for this robot is those two functions, in some order, with your other mechanisms mixed in.

## How to use this guide

This guide has two halves, and they are meant to be read differently.

| Part | What it is | How to read it |
| --- | --- | --- |
| **Part 1 — Tutorial** | Step-by-step instructions to get from an empty project to a robot that drives itself. | At the robot, with the template open next to you. Do the steps in order. |
| **Part 2 — Explanation** | The theory: what PID actually does, why we use inches, how headings work, what the gear ratio math means. | In a chair, whenever you want to know why something works. |

You do not have to read Part 2 before Part 1. Plenty of good programmers get the robot moving first and get curious second. But do read it eventually — tuning a robot you understand is a completely different experience from guessing.

---

# Before You Start

## What you need

- A mostly finished robot with a 6-motor drivetrain (3 motors per side).
- An Inertial Sensor (IMU) plugged into the brain.
- A V5 controller — you need it to drive, and it makes downloading code easier.
- VEXcode V5 installed on your computer. The web version works in a pinch, but the desktop app is strongly recommended.
- The template file, `74074Y_Drivetrain_Template.cpp`.

## Three things you need to know about your robot

Go measure these before you write a single line. Guessing here is the number one reason a robot drives the wrong distance.

| What | How to find it | Example |
| --- | --- | --- |
| **Wheel diameter** | It is usually printed on the wheel. Measure across the middle if it is not. | 2.75", 3.25", or 4" |
| **Gear ratio** | Count the teeth on the gear attached to the motor, then the teeth on the gear attached to the wheel axle. Divide motor ÷ wheel. | 36t motor → 48t wheel = 36 ÷ 48 = 0.75 |
| **Ports** | Look at the brain. Write down which port every drivetrain motor and the inertial sensor is plugged into. | L1 = port 1, L2 = port 2, IMU = port 20 |

**Direct drive?** If your motors are attached straight to the wheels with no gears in between, your gear ratio is 1.0.

## Make a folder. Save versions. Please.

Before you touch the code, make a dedicated folder for your robot code — in Google Drive, on your desktop, on a flash drive. Do all three if you can. Put the template in it and rename it to something you will recognize later, like:

```
74074Y_Main_Robot_Code.cpp
```

Then save a new copy every time you make a change that works. Not every change — every change *that works*. Name them with dates:

```
74074Y_Main_11-04_working-auton.cpp
74074Y_Main_11-06_tuned-turns.cpp
```

This feels like a waste of time right up until the afternoon you delete something important two days before a competition. Then it is the best habit you ever built.

> **On this repo:** if you're managing your code with Git (like this repo does), a commit history does this job for you automatically — see the main README for the workflow.

---

# Part 1 — Tutorial: From Zero to a Driving Robot

Do these steps in order. Each one ends with a checkpoint — something you can see the robot do. If a checkpoint fails, stop and fix it before moving on. Skipping ahead with a broken step is how you end up with five problems at once and no idea which is which.

**Have the template open.** Keep `74074Y_Drivetrain_Template.cpp` open next to this guide the whole way through. The zone names in the code match the step names here.

## Step 1 — Make a new C++ project

- Open VEXcode V5.
- File → New Text Project (this is the C++ one). If it asks, choose V5 as the platform.
- Save it into the folder you made, with your real filename.
- Select everything already in the editor and delete it.

Leave the empty project open. You will paste the template in shortly — but configure your devices first, in Step 2, so the names in the code have something to point at.

## Step 2 — Zone A: tell VEXcode what is plugged in

Zone A of the template is the only zone you never type in. VEXcode writes it for you based on what you enter in the Devices menu.

- Click the **DEVICES** button at the top right of VEXcode.
- You should already see `Controller1`. Leave it alone — that is your controller.
- Click **ADD A DEVICE** and choose **Motor**. Do this once for each drivetrain motor — six times for a 6-motor drive.
- Name each motor something you will understand: `LeftFront`, `LeftMiddle`, `LeftBack`, `RightFront`, `RightMiddle`, `RightBack`. (Or `L1`, `L2`, `L3`, `R1`, `R2`, `R3` — just be consistent.)
- For each motor, set the **port number** to match what is physically plugged into the brain.
- Set the **motor cartridge** — the colored insert. Green is 200 rpm and is the normal choice for a drivetrain. Red is 100 rpm (torque), blue is 600 rpm (speed).
- Set **REVERSED** for the motors that need it. Usually this is the three left motors, but not always — it depends on how your gearboxes are built.
- Click **ADD A DEVICE** again, choose **Inertial**, name it `Inertial1`, and set its port.

**This is the step people get wrong.** A wrong port or a motor reversed the wrong way will make the robot spin in place, drive backward, or tear itself apart. Check every one against the physical robot before you move on.

Now paste the template into `main.cpp`, replacing everything.

## Step 3 — Zone B: enter your robot's numbers

Scroll to Zone B. There are three things to change.

### 3a. Motor group names

Replace the six names below with exactly what you typed in the Devices menu. Spelling and capitalization must match.

```cpp
motor_group left_motors  = motor_group(LeftFront,  LeftMiddle,  LeftBack);
motor_group right_motors = motor_group(RightFront, RightMiddle, RightBack);
```

A motor group lets you command three motors with one line, exactly like the three motors on one side of your drivetrain always move together.

### 3b. Inertial sensor name

```cpp
inertial &IMU = Inertial1;
```

This gives your sensor a nickname. The rest of the code says `IMU`, so you only have to change this one line if you named yours something else.

### 3c. Wheel diameter and gear ratio

```cpp
const double WHEEL_DIAMETER = 3.25;
const double GEAR_RATIO     = 0.75;
```

The gear ratio is always **motor gear teeth ÷ wheel gear teeth**. Some examples:

| Setup | Math | GEAR_RATIO |
| --- | --- | --- |
| 36t on motors → 48t on wheels (common torque drive) | 36 ÷ 48 | 0.75 |
| 60t on motors → 36t on wheels (speed drive) | 60 ÷ 36 | 1.6667 |
| Direct drive, no gears | — | 1.0 |

**Checkpoint** — Zone B now describes your actual robot. Nothing moves yet; that is Step 5.

## Step 4 — Zone C: leave it alone for now

Zone C is full of tuning numbers — the PID gains, tolerances, and timeouts. The values in the template are reasonable starting points for a typical 6-motor robot on 3.25" wheels, and they will get your robot moving sensibly. They will almost certainly not be perfect for your robot.

That is fine. Get it moving first (Steps 5–6), then tune (Steps 7–9). Changing tuning numbers before you have ever seen the robot move is guessing.

## Step 5 — Download and test driver control

Plug the controller into the computer, or plug the brain in directly. Hit **Download**, then **Run**.

The brain screen will say it is calibrating the IMU. Do not touch or move the robot for about two seconds. Then the auton selector screen appears.

Now drive it. By default the template uses arcade drive: the left stick moves forward and backward, the right stick turns.

**Checkpoint** — push the left stick forward and the robot drives forward. Push the right stick right and the robot turns right.

| What happens | What it means | Fix |
| --- | --- | --- |
| Robot spins in place when you push forward | One side is reversed and the other is not. | Devices menu — flip the REVERSED setting on one whole side. |
| Robot drives backward | Both sides are reversed. | Devices menu — flip REVERSED on all six motors. |
| Robot turns the wrong way | Left and right motor groups are swapped in Zone B. | Swap the names in the two `motor_group` lines. |
| One wheel drags | A motor is on the wrong port, or its cartridge is set wrong. | Check that motor in the Devices menu against the brain. |

Prefer tank drive? In Zone C, change `USE_ARCADE_DRIVE` to `false`.

## Step 6 — Your first autonomous move

Put the robot on the field with the back of it against a wall, or on a piece of tape. The selector on the brain screen starts on route 1, "Drive Forward", which drives 24 inches and stops.

- Make sure the selector says `1. Drive Forward`. Tap the brain screen to cycle if it does not.
- Give the robot room — at least three feet of clear space ahead.
- Run the autonomous. If you have a competition switch, enable autonomous. If not, temporarily call `run_selected_auton()` from `driver_control()` to test, then remove it.
- Measure how far it actually went with a tape measure.

**Checkpoint** — the robot moves forward roughly two feet and stops. "Roughly" is fine right now. If it went a wildly wrong distance — half, or double — recheck `WHEEL_DIAMETER` and `GEAR_RATIO` before you touch any PID numbers.

**A quick sanity check.** If you asked for 24 inches and got about 18, your gear ratio is probably wrong or inverted. See [From inches to motor degrees](#from-inches-to-motor-degrees-the-gear-ratio) in Part 2 — that one number is the most common source of distance errors.

## Step 7 — Tune drive_distance

Now make the distance accurate. You are adjusting two numbers in Zone C, one at a time, always testing the same move (route 1, 24 inches).

```cpp
double DRIVE_kP = 0.260;   // push
double DRIVE_kD = 1.500;   // brake
```

Change one number, download, run, measure. Write down what you tried and what happened — the PID Tuning Log in this folder is built for exactly this.

| Symptom | What it means | What to change |
| --- | --- | --- |
| Stops well short and gives up | Not enough push near the end. | Raise `DRIVE_kP` a little (try +0.05). |
| Shoots past the target, then comes back | Too much push, not enough brake. | Raise `DRIVE_kD` (try +0.5), or lower `DRIVE_kP`. |
| Rocks forward and back and never settles | Way too much kP, or too much kD. | Cut `DRIVE_kP` in half. Retune from there. |
| Crawls the last few inches very slowly | kP is fine but the robot is fighting friction. | Raise `MIN_MOVE_POWER` by 1 or 2. |
| Accurate at 24" but wrong at 48" | That is not tuning — that is a measurement error. | Recheck `WHEEL_DIAMETER` and `GEAR_RATIO`. |

Stop when the robot lands within about half an inch of the target and does not visibly bounce. That is good enough to win matches.

## Step 8 — Tune turn_to_angle

Same process, different numbers. Test with a 90-degree turn — route 3 (Square) is a good one, or write a two-line test routine.

```cpp
double TURN_kP = 0.900;
double TURN_kD = 2.000;
```

| Symptom | What to change |
| --- | --- |
| Stops short of the angle | Raise `TURN_kP` (try +0.1). |
| Overshoots and swings back | Raise `TURN_kD` (try +0.5). |
| Shakes back and forth at the end | Lower `TURN_kP`, or raise `TURN_kD`. |
| Turns extremely slowly | Raise `TURN_kP`, or raise `TURN_MAX_POWER`. |
| Turns the wrong direction | Left and right motor groups are swapped in Zone B. |

**Turns are surface-dependent.** A robot tuned on carpet will behave differently on foam field tiles. Tune on the surface you will compete on.

## Step 9 — Make it drive straight

Run route 1 again and watch the robot from behind. If it curves, one side has more friction or grip than the other. The code already fights this using the inertial sensor — it just may not be fighting hard enough.

```cpp
double DRIVE_HEADING_kP = 2.000;
```

- Robot still drifts to one side → **raise** it (try 3.0).
- Robot snakes back and forth as it drives → **lower** it (try 1.0).

This one number is worth getting right. A 24-inch drive that ends 4 degrees off will throw off every move that comes after it.

## Step 10 — The square test

Select route 3 (Square). Put a piece of tape on the floor at one corner of the robot and run it.

The robot drives 24 inches, turns 90 degrees, and repeats four times. If your tuning is good, it comes back to the tape facing the same direction it started.

| Result | What it tells you |
| --- | --- |
| Ends on the tape, facing forward | Distance and turns are both good. You are done tuning. |
| Ends short or long of the tape but square | Distance tuning — go back to Step 7. |
| Ends on the tape but rotated | Turn tuning — go back to Step 8. |
| Drifts sideways into a parallelogram | Heading correction — go back to Step 9. |

The square test is the single best diagnostic you have, because it separates the three kinds of error. Use it every time you change anything mechanical.

## Step 11 — Write your own autonomous routine

Go to Zone E. The six sample routes are there so you can test — they do not score anything. Replace them with real ones.

A routine is just a list of moves:

```cpp
void auton_left_side() {
  drive_distance(30);      // drive to the goal
  turn_to_angle(90);       // face right
  drive_distance(12);      // line up
  // ... your intake / piston commands go here ...
  drive_distance(-18);     // back away
  turn_to_angle(180);      // turn around
}
```

Remember that one field tile is 24 inches. If you can count tiles, you can estimate a route without measuring anything.

**Headings are absolute, not relative.** `turn_to_angle(90)` means "face 90 degrees", not "turn 90 more degrees". That is a feature — small errors do not pile up over a routine. See [The 360-degree heading plane](#the-360-degree-heading-plane) in Part 2.

To add your own routine to the selector: write the function, add a case to `run_selected_auton()`, add its name to `auton_names`, and bump `NUM_AUTONS`.

**Challenge** — write a routine that scores a matchload into one of the goals. Start by writing the moves in plain English on paper, then translate each line into a `drive_distance` or `turn_to_angle` call.

## Step 12 — Use the selector at a competition

All of your routes are loaded onto the robot at once. Before a match, tap the brain screen to cycle to the one you want. The screen shows which is selected.

Do this after the robot is on the field and before the match starts — and always double-check the screen. Running the wrong autonomous is a classic, avoidable way to lose a match.

## Troubleshooting

| Problem | Likely cause | Fix |
| --- | --- | --- |
| Robot does nothing in autonomous | IMU still calibrating, or autonomous never got enabled. | Wait for the selector screen before starting. Check your competition switch. |
| Every turn is wrong by the same amount | The robot was moved while the IMU calibrated. | Restart the program and hold still during calibration. |
| Headings drift over a long routine | IMU drift, or the sensor is loose on the robot. | Make sure the inertial sensor is bolted down solidly, not zip-tied. |
| Moves are accurate alone, wrong in a sequence | Wheels are slipping during turns, so the encoders lie. | Lower `TURN_MAX_POWER`; add a short wait between moves. |
| Robot times out mid-move | It is stuck, or the timeout is too short for a long drive. | Raise `DRIVE_TIMEOUT_MS`. If it is physically stuck, that is the timeout doing its job. |
| Code will not compile | A motor name in Zone B does not match the Devices menu. | Read the error — it names the identifier it cannot find. |

---

# Part 2 — Explanation: How and Why It Works

Part 1 told you what to type. This part tells you why. None of it is required to make the robot move — all of it is required to fix the robot when it stops moving correctly.

## Why C++?

VEXcode gives you three languages: Blocks, Python, and C++. Blocks is the fastest way to get something moving. Python is a comfortable middle ground. C++ is what most top VEX teams use, and it is worth the extra brackets for three reasons.

- **Speed.** C++ compiles to machine code that runs directly on the brain. A PID loop running every 20 milliseconds has time to spare.
- **Control.** You get direct access to motor and sensor APIs, precise timing, and the ability to structure code however you like.
- **Transfer.** C++ is a real engineering language. The same syntax shows up in embedded systems, robotics research, game engines, and firmware. Learning it on a VEX robot is learning it for everything after.

## What PID actually is

PID is a way of answering one question, over and over, many times a second:

*"I want to be over there. I am here. How hard should I push?"*

The gap between where you want to be and where you are is called the **error**. PID looks at that error three different ways and adds the answers together.

### P — Proportional: how far away am I?

Push harder when the error is big, gentler when it is small. This is the workhorse — it does most of the actual moving.

*Analogy:* you press the gas harder when the stop sign is far away, and ease off as you get close.

On its own, P has a problem. As the error shrinks, the push shrinks, so the robot creeps toward the target slower and slower. And because a moving robot has momentum, P alone tends to sail right past the target and then correct back — oscillation.

### D — Derivative: how fast am I closing the gap?

D looks at how quickly the error is shrinking and pushes back against it. The faster you are approaching, the harder D brakes.

*Analogy:* easing off the gas as you approach the parking spot, because you can see how fast the gap is closing.

D is what stops the overshoot that P causes. In the code, it is the simplest possible version — how much the error changed since the last loop, 20 milliseconds ago:

```cpp
double derivative = error - prev_error;
```

**Why `prev_error` is seeded, not zeroed.** On the very first pass through the loop there is no previous error yet. If you start `prev_error` at 0, the first derivative comes out as the entire error — a huge fake number that makes the robot jerk. The template measures the error once before the loop and starts `prev_error` at that value, so the first derivative is exactly 0. Small detail, visibly smoother start.

### I — Integral: what have I been putting up with?

I adds up all the error over time. If a small error refuses to go away — the robot is stopping a quarter inch short every single time — the accumulated total grows until the robot finally pushes through it.

*Analogy:* nudging the steering wheel a bit more and a bit more because the car keeps drifting left, no matter what you do.

### Why this template leaves I at zero

Integral is genuinely useful for fighting steady resistance — a heavy arm sagging under gravity, for instance. For a drivetrain doing short moves, it mostly causes a problem called **integral windup**: the accumulated error builds up while the robot is far away, and then keeps pushing after the robot has arrived, causing overshoot.

A well-tuned PD controller handles a drivetrain fine. Adding I means also adding windup protection, which is more complexity for very little gain. So the template uses P and D, and leaves I for when you actually need it.

## Why we use inches

The motors do not know what an inch is. They count their own rotation in degrees. We could write the whole program in motor degrees — and it would work, and it would be miserable.

Engineers use units humans can reason about. You can look at a field and estimate 30 inches. You cannot look at a field and estimate 1,410 motor degrees. When your route is written in inches, you can plan it on paper, sanity-check it with a tape measure, and spot a mistake instantly.

**The most useful number in VEX.** One field tile is exactly 24 inches. Count tiles, multiply by 24, and you have a route.

## The 360-degree heading plane

The inertial sensor reports the robot's heading like a compass, from 0 up to 359.9 degrees.

| Heading | Direction |
| --- | --- |
| 0° | Straight ahead — wherever the robot was facing when the program started |
| 90° | Right |
| 180° | Behind |
| 270° | Left |
| 360° | Back to 0° |

Turning right increases the number. Turning left decreases it. If the robot is at 0 degrees and turns 1 degree left, its heading becomes 359 — not -1.

The robot's "north" is set by whichever way it is facing when the code starts, unless you call `IMU.setHeading()` yourself. This means how you place the robot on the field before a match matters as much as the code.

### Why wrapping matters

Say the robot is at 350 degrees and you ask it to turn to 10 degrees. Subtract them naively and you get 10 − 350 = −340, which tells the robot to spin almost all the way around the wrong way. The real answer is +20 degrees — a small turn to the right.

The fix is a helper function that folds any angle back into the range −180 to +180:

```cpp
double wrap_180(double angle) {
  while (angle >  180) angle -= 360;
  while (angle < -180) angle += 360;
  return angle;
}
```

Every angle difference in the template goes through `wrap_180`, which is why the robot always takes the short way around. It will never spin 340 degrees when a 20-degree turn will do.

## From inches to motor degrees (the gear ratio)

This is the conversion at the heart of `drive_distance`, and the place where a single wrong operation quietly ruins every autonomous routine you write.

Three steps get you from an inch to a motor degree:

1. How many times must the **wheel** spin? `inches ÷ wheel circumference`
2. In degrees, that is: `× 360`
3. How far must the **motor** spin to make the wheel do that? `÷ GEAR_RATIO`

```cpp
double inches_to_motor_degrees(double inches) {
  return (inches / WHEEL_CIRCUMFERENCE) * 360.0 / GEAR_RATIO;
}
```

### Why the last step is a divide

Gears trade speed for torque. With a 36-tooth gear on the motor driving a 48-tooth gear on the wheel, the wheel turns slower than the motor — so the motor has to spin *more* than the wheel does to cover the same ground.

`GEAR_RATIO` for that setup is 36 ÷ 48 = 0.75. Dividing by 0.75 is the same as multiplying by 1.333, which is exactly the "motor spins more" we want.

Multiplying instead would say the motor should spin *less* than the wheel, which is backwards. Here is what that costs on a real robot:

| You ask for | Correct (÷ 0.75) | Backwards (× 0.75) | Robot actually travels |
| --- | --- | --- | --- |
| 24 inches | 1,128 motor degrees | 635 motor degrees | 13.5 inches |

Nearly eleven inches short, every single move, compounding across a routine. And because the error scales with distance, it looks like a tuning problem — which is why people spend hours adjusting PID gains that were never the issue.

**How to catch it.** Ask for exactly 24 inches and measure. If the result is off by a consistent *percentage* rather than a consistent *amount*, the problem is the conversion, not the tuning.

## How the robot drives straight

Encoders count wheel rotation, not distance across the floor. If the left wheels have slightly better grip than the right, both sides count the same rotations while the robot quietly curves. The encoders think everything is fine.

The inertial sensor is the fix, because it measures which way the robot is actually pointing. In every loop of `drive_distance`, the code compares the current heading against the heading it started at, and adds a small difference between the two sides:

```cpp
double heading_error = wrap_180(start_heading - IMU.heading(degrees));
double correction    = heading_error * DRIVE_HEADING_kP;

left_motors.spin(forward,  power + correction, percent);
right_motors.spin(forward, power - correction, percent);
```

One side speeds up, the other slows down by the same amount, and the robot curves back onto its original heading. This is a P controller on top of the main P controller — the same idea, doing a different job.

### What about driving backward?

It is natural to assume the correction has to flip sign when the robot drives in reverse. It does not — as long as the power stays a **signed** number, the way it does in this template.

Here is why. How fast a robot rotates depends only on the **difference** between the two sides, never on whether both sides happen to be going forward or backward. In the code above, that difference is:

```
(power - correction) - (power + correction)  =  -2 × correction
```

The power cancels out completely. Whether it is +60 or −60, the steering effect is identical, so the same correction steers the robot correctly in both directions.

**Where the flip is genuinely needed.** Some templates write `spin(reverse, magnitude)` with a positive magnitude instead of `spin(forward, signedPower)`. Reversing the direction flips the sign of the difference too, so those versions really do have to negate the correction for backward moves — and it is an easy thing to forget. Keeping power signed sidesteps the whole trap.

## Tolerance, settle time, and timeout

A PID loop will chase a target forever if you let it. Three numbers tell it when to stop.

| Setting | Question it answers | If it is too small | If it is too big |
| --- | --- | --- | --- |
| **Tolerance** | How close is close enough? | The robot never declares itself finished and always hits the timeout. | The robot stops noticeably short or long. |
| **Settle time** | How long must it stay there? | It declares victory while still coasting through the target. | Every move has a visible pause at the end — costly in a 15-second auton. |
| **Timeout** | When do we give up? | Long moves get cut off partway. | A stuck robot burns the whole autonomous period grinding into a wall. |

Settle time is the one beginners skip, and it matters. Without it, a robot flying through the target at speed passes within tolerance for one loop, calls itself done, and coasts several inches past. Requiring it to stay within tolerance for 150 milliseconds means it has actually stopped there.

## Arcade vs. tank drive

| Mode | How it works | Good for |
| --- | --- | --- |
| **Arcade** | One stick controls forward and backward, the other controls turning. The code mixes them: left = drive + turn, right = drive − turn. | Most drivers. Easier to drive a smooth curve, easier to go perfectly straight. |
| **Tank** | Left stick controls the left side, right stick controls the right side. No mixing. | Drivers who came from other robotics programs, and precise pivot-in-place work. |

Neither is better. Switch with `USE_ARCADE_DRIVE` in Zone C, and let whoever actually drives the robot decide.

The **deadband** is a small companion setting. Joysticks rarely read exactly zero when released, so the code ignores any reading smaller than a few percent. Without it, the robot creeps across the field on its own.

## Going further

Everything below is deliberately left out of the template to keep it readable. Each is a good next project once your robot is reliably driving squares.

### Acceleration ramping (slew rate limiting)

Right now, a drive command can jump from 0% to 80% power in a single 20-millisecond loop. On a heavy robot that means the wheels break traction and spin, and once they slip the encoders are counting rotation that never became distance.

Slew rate limiting caps how much the power is allowed to change per loop — say, 10% — so the robot accelerates smoothly instead of lurching. It typically improves consistency more than any amount of PID tuning on a robot heavy enough to slip.

The idea in one line:

```cpp
if (power > last_power + MAX_CHANGE) power = last_power + MAX_CHANGE;
if (power < last_power - MAX_CHANGE) power = last_power - MAX_CHANGE;
last_power = power;
```

Add it once you understand the PID loop well enough to debug both at the same time.

### Adding an integral term

If you get to the point where the robot consistently stops a hair short and no amount of P and D tuning fixes it, an integral term is the right tool. Accumulate the error each loop, multiply by a small kI, and add it to the output — then add windup protection: only accumulate when the error is already small, and reset the accumulator when the error changes sign.

### Odometry

Instead of tracking one distance at a time, odometry tracks the robot's full (x, y, heading) position on the field continuously, usually with unpowered tracking wheels. It lets you write `drive_to_point(x, y)` instead of chaining drives and turns, and errors stop compounding across a routine. This is a substantial project and the natural sequel to this template.

### Motion profiling

Rather than reacting to error, motion profiling plans the entire speed curve of a move in advance — accelerate to a cruise speed, hold it, decelerate to arrive exactly on target. Combined with PID it produces the very smooth, fast, repeatable movement you see from top teams.

---

# Appendix A — Zone Map

The template is split into seven zones so you always know where to look.

| Zone | What is in it | Do you edit it? |
| --- | --- | --- |
| **A** — Device configuration | The list of motors, sensors, and ports. | No — VEXcode writes it from the Devices menu. |
| **B** — Motors & measurements | Motor groups, IMU nickname, wheel diameter, gear ratio. | **Yes** — every robot is different. Step 3. |
| **C** — Tunable parameters | PID gains, tolerances, timeouts, power limits, drive mode. | **Yes** — after the robot moves. Steps 7–9. |
| **D** — Movement functions | `drive_distance`, `turn_to_angle`, and their helpers. | No — not until you understand Part 2. |
| **E** — Autonomous routines | The six sample routes and the brain-screen selector. | **Yes** — this is where your real routes go. Step 11. |
| **F** — Driver control | Joystick reading, arcade/tank mixing, intake and piston. | **Yes** — add your own mechanisms here. |
| **G** — Main program | IMU calibration, selector loop, competition callbacks. | No. |

**Optional mechanisms.** Zone B has two switches, `HAS_INTAKE` and `HAS_PISTON`, both set to 0. The intake and piston code in Zone F is skipped entirely while they are 0, so the template compiles on a drivetrain-only robot. Create the device in the Devices menu first, then change the 0 to a 1.

# Appendix B — Quick Reference

## The two functions

```cpp
drive_distance(24);     // forward 24 inches (one field tile)
drive_distance(-12);    // backward 12 inches
turn_to_angle(90);      // face 90 degrees (absolute, not relative)
turn_to_angle(0);       // face the starting direction again
```

## Numbers worth memorizing

| Thing | Value |
| --- | --- |
| One field tile | 24 inches |
| Gear ratio | motor gear teeth ÷ wheel gear teeth |
| Heading | 0° = start, 90° = right, 180° = behind, 270° = left |
| PID loop rate | every 20 ms (50 times a second) |
| Autonomous period | 15 seconds |

## Tuning cheat sheet

| Symptom | Change |
| --- | --- |
| Stops short | Raise kP |
| Overshoots | Raise kD (or lower kP) |
| Oscillates / shakes | Lower kP |
| Curves while driving straight | Raise `DRIVE_HEADING_kP` |
| Snakes while driving straight | Lower `DRIVE_HEADING_kP` |
| Wrong by a consistent percentage | Not tuning — check `WHEEL_DIAMETER` and `GEAR_RATIO` |

If anything in this guide is unclear, ask. That is what mentors are for. Have fun coding.
