# Self-Tuning PID for 74074Y Drivetrain Template — Consolidated Brainstorm

Status: BRAINSTORM ONLY. Nothing here is committed to the beginner guide or
base template yet. This is a "going further" side-project being explored
alongside the main Tutorial/Explanation deliverable. Fits the existing
project's philosophy: keep the core template simple, defer advanced stuff
(like this) to optional callouts.

Context: base template already has drive_distance() and turn_to_angle() with
the gear-ratio bug fixed, prev_error seeding fixed, and reverse-driving sign
fixed. This doc is about a POSSIBLE future auto-tuning add-on for those same
two functions, plus a related drivetrain-balance calibration idea.

---

## 1. THE CORE LOOP

Self-tuning = run a fixed test movement -> log data -> score the result ->
adjust gains -> repeat, within a time budget. Not fundamentally different
from what a human does with a stopwatch and a notebook; the win is just
automating the boring iteration and keeping a real log.

Two totally separate tuning targets, matching the two movement functions:
  - turn_to_angle()  -> TURN_kP, TURN_kI, TURN_kD
  - drive_distance() -> DRIVE_kP, DRIVE_kD, DRIVE_HEADING_kP

Plus a THIRD, separate concept (calibration, not tuning) covered in section 6.

---

## 2. TEST DESIGN

Need a fixed, repeatable, isolated movement per trial (not a full auton
routine) so trials are comparable:
  - Turn tuning: fixed turn amount(s) from wherever the robot currently sits.
    User confirmed the robot is free to spin anywhere -- no need to return to
    a fixed start heading between trials, which saves time per trial.
  - Drive tuning: fixed distance(s), e.g. 24-48in.
  - IMPORTANT: test across MULTIPLE angles/distances per round, not just one
    repeated value (e.g. rotate through +90, -135, +45 across trials) --
    guards against overfitting to one specific test condition. This is a
    documented real failure mode (see section 8, Twiddle-in-the-wild).

## 3. DATA LOGGING PER TRIAL

During each trial, log a fixed-size array every 20ms (matches existing
LOOP_MS in the template):
  (time_ms, error_deg or error_in, power_pct)

CRITICAL: do NOT printf/log-to-serial INSIDE the tight 20ms control loop --
that would perturb the very timing being measured. Log to a RAM array during
the loop, dump/print it all AFTER the trial completes.

## 4. CLASSIFYING A TRIAL (coarse phase)

Before/instead of pure numeric optimization, first classify the shape of the
error curve to jump toward the right neighborhood quickly. This is literally
automating what LemLib/JAR's manual docs already tell a human to do (see
section 7) -- not inventing new theory.

Symptom (from the logged error curve)      -> Likely cause   -> Coarse fix
--------------------------------------------------------------------------
Error shrinks very slowly, times out         Not enough push    Raise kP
  without ever entering tolerance band
Error crosses zero 3+ times, NOT decaying    Too much push,     Lower kP,
                                              not enough damping raise kD
Error crosses zero once/twice then settles   Slight overshoot   Raise kD
                                                                 a bit
Gets close, plateaus off-target, never       Static friction    Add/raise
  quite reaches zero-crossing                beats P term at    kI (small
                                              small error, OR    steps only,
                                              needs a min-power  see below),
                                              floor              or raise
                                                                 MIN_MOVE_POWER
Reaches tolerance fast, no overshoot,        GOOD                Move to fine
  stays there                                                    phase / done

Simple classifier pseudocode:
  - count zero-crossings of error across the logged trial
  - track whether error ever entered tolerance band at all
  - look at final error value
  -> bucket into TOO_SLOW / OSCILLATING / OVERSHOOT_ONCE / STEADY_STATE_OFFSET / GOOD

## 5. COST FUNCTION -- IMPORTANT UPDATE FROM USER'S REAL EXPERIENCE

Original idea (WRONG for this team's goals): blend overshoot + settle time +
final error into one weighted score, overshoot merely penalized.

CORRECTED based on user's team's actual historical tuning philosophy:
  - Goal = AS FAST AS POSSIBLE
  - ZERO overshoot, ZERO oscillation allowed -- not "minimized", DISALLOWED
  - Tolerance is a dead-zone, not a point target: landing anywhere in
    [target - 1deg, target + 1deg] is a full success (e.g. asked for 179,
    landed on 180 -> totally fine, no penalty)

This means overshoot must be a HARD GATE, not a weighted term:

  if error crosses zero from the correct-approach side (i.e. true overshoot
     -- passed through/past the target and had to be pulled back):
      trial = FAILED regardless of speed (cost = infinity / disqualified)
  else:
      cost = time_to_first_enter_and_remain_in_tolerance_band

Twiddle (or any search) then only ever compares SPEED among trials that never
overshot at all. This naturally biases the search toward what controls
folks call "critically damped" -- push kP as high as possible while raising
kD just enough to prevent ever crossing zero. This is a cleaner, more
teachable target than a blended score, AND it matches how this team actually
wants their robot to behave in competition.

Practical detection: watch the sign of error over time. If robot starts with
error > 0 (needs to turn right, say) and error EVER goes negative during the
trial, that's overshoot -> disqualify. Entering the +-1deg tolerance band
without ever having gone negative first = clean success.

## 6. SEARCH ALGORITHM: TWIDDLE

Chosen because: no derivative needed, naturally slows down near convergence,
well-suited to "trials are physically expensive" (each trial costs seconds +
battery + motor wear, can't afford hundreds of them).

Per-gain independent step sizes -- CONFIRMED IMPORTANT by outside precedent
(section 8): do NOT start all three step sizes equal. kI's useful range is
much smaller than kP/kD's, so its initial step size should start much smaller
too, or it thrashes for many iterations before settling.

High-level loop:
  for each gain in rotation (kP, kI, kD):
    try gain + step
    if new cost is better (respecting the hard overshoot gate above):
        keep it, grow step (explore more aggressively)
    else:
        try gain - step instead
        if that's better: keep it, grow step
        else: revert to original value, shrink step (converging)
  repeat until time budget (5 min) exhausted or all steps shrink below
  a "done" threshold

Given the hard-gate cost function, expect the search to spend a lot of its
early trials just finding ANY gain combo that avoids overshoot at all (which
may itself look like the TOO_SLOW/coarse-phase problem) before it starts
optimizing for speed among safe options. Coarse phase (section 4) exists
specifically to get to "no overshoot" territory fast, so Twiddle isn't
wasting trials searching blind.

## 7. GOOD STARTING RANGES / SAFETY RAILS (not final answers, just bounds)

Purpose: keep blind search from wandering into violent/unstable territory,
and give a reasonable starting point for a team that hasn't tuned at all.
JAR-Template ships default gains "tuned to a six motor 360RPM drivetrain" as
a similar starting point -- confirms this pattern is normal/expected in the
VEX ecosystem, not a hack.

  TURN_kP           range: 0.3 - 1.5
  TURN_kD           range: 0.5 - 4.0
  TURN_kI           range: 0.0 - 0.02   (rarely needs to move much at all)
  DRIVE_kP          range: 0.1 - 0.6
  DRIVE_kD          range: 0.3 - 2.5
  DRIVE_HEADING_kP  range: 0.5 - 3.0

These are safety rails / plausible starting neighborhoods for "most" 6-motor
VEX drivetrains, not universal truths -- could be refined once we find real
documentation of someone else's autotuner implementation (still TBD, user
may find something).

## 8. VALIDATION FROM REAL-WORLD PRECEDENT (web research findings)

### LemLib docs (docs/tutorials/4_pid_tuning.md) -- MANUAL procedure only,
no autotuner shipped. But their manual flowchart IS basically our classifier,
described in English:
  1. Zero out kI, anti-windup, exit conditions, slew FIRST. Tune kP+kD alone.
  2. "Repeat until no amount of kD stops the robot from oscillating" -- i.e.
     push kP up until oscillation appears, raise kD to damp it; if NO kD can
     stop the oscillation at a given kP, that kP is too high, back it off.
     This is exactly our OSCILLATING branch, just done by a human.
  3. kI explicitly called "a last resort... which is rare" -- independently
     confirms the user's team's real experience of barely touching I.
  4. kI tuning (when needed): measure AVERAGE steady-state error over MANY
     trials across a range of motion sizes (10-180deg turns / 5-48in drives),
     multiply by 1.5, that becomes an "anti-windup range" -- integral only
     accumulates INSIDE that error band, zeroed outside it. This is a more
     rigorous anti-windup design than a hard clamp on accumulated integral
     (which is what our CURRENT base template does) -- worth considering as
     an upgrade regardless of whether autotune ever gets built.
  5. Slew (acceleration limiting) tuned oppositely to other gains: start
     HIGH (basically off), LOWER until a specific symptom disappears (wheel
     slip without a dedicated tracking wheel, OR physical tipping on a heavy
     robot). Only relevant in those two specific situations, otherwise skip.
  6. Exit conditions are TWO-TIERED in LemLib, not single-tolerance like our
     template: e.g. "within 5in for 500ms, exit" OR "within 1in for 100ms,
     exit" -- whichever triggers first. Lets a decent-but-imperfect arrival
     finish quickly via the looser/longer-timeout tier, while a great
     arrival exits almost instantly via the tighter/shorter-timeout tier.
     Relates directly to the "179 vs 180 is fine" flexibility -- could be a
     "going further" mention even independent of autotuning.

### JAR-Template -- also MANUAL only, no autotuner. Same "startI" concept as
LemLib's anti-windup range, different name: integral only begins accumulating
below a fixed error threshold (e.g. 15deg for turning). Two unrelated
libraries independently landing on the same anti-windup fix = good signal
it's the standard/correct approach, not just one team's preference.

CONFIRMED: neither of the two most popular VEX libraries auto-tunes. What
we're brainstorming is a step beyond ecosystem standard practice, not
reinventing something that already exists. Good framing if this ever ships:
"this automates the exact procedure LemLib/JAR tell you to do by hand."

### Outside VEX -- real Twiddle implementations (Udacity Self-Driving Car
Nanodegree PID projects, C++, tuning steering against cross-track error):
  - kI consistently converges to near-zero/negligible after kP+kD are
    properly tuned (one project's final kI: 0.00018). Independently confirms
    the user's team's real-world finding.
  - Per-gain step sizes should NOT start equal -- one dev's kI step size was
    way oversized relative to kP/kD and thrashed for dozens of iterations
    before shrinking down. Directly informs section 6 above.
  - Twiddle can get stuck in a local minimum / overfit if tested on too
    narrow a set of conditions (one dev tuned only on straight track, car
    then handled curves badly). Confirms multi-condition testing (section 2)
    is addressing a real, documented failure mode, not just theoretical
    caution.
  - Twiddle is a well-established, standard choice for exactly this problem
    shape (few continuous gains, no gradient available, trials are somewhat
    costly) -- good validation of the section 6 pick.

STILL TO DO: user may find additional documentation of someone else's actual
VEX autotuner (not just manual flowcharts) -- would want to compare whatever
parameters/approach they used against everything above.

---

## 9. GRAPHING / VISUALIZATION

User open to moving this specific workflow to VS Code + VEX extension instead
of staying inside VEXcode's own IDE, since it's a more real dev environment.

Pipeline sketch:
  1. Log (time_ms, error, power) arrays in RAM during each trial (per
     section 3's no-printf-in-loop rule).
  2. After each trial (or after the whole run), dump the log as CSV-ish
     lines via printf() over the existing USB serial console -- no new
     tooling needed, this channel already exists for any VEXcode/PROS project.
  3. MVP: paste terminal output into a spreadsheet, or paste it into a Claude
     conversation/artifact for an instant chart. Zero extra tooling.
  4. Stretch: small companion Python script (pyserial + matplotlib) that
     reads the live serial stream and plots error-vs-time / power-vs-time
     per trial automatically. More setup, nicer live-feedback loop.
  5. BEST TEACHING VISUAL: log cost-per-trial across the WHOLE 5-minute
     autotune run, plot cost vs trial number at the end. Watching the score
     visibly ratchet down every few attempts makes "search algorithm" a
     concrete, intuitive idea instead of an abstract one -- probably the
     single most valuable visualization to actually build if any of this
     gets built at all.

---

## 10. DRIVETRAIN BALANCE CALIBRATION (separate from PID tuning entirely)

User's key insight: two motors can have EQUAL friction/mechanical setup on
both sides of the drivetrain, but still cause the robot to drift straight-line
due to motor-to-motor POWER OUTPUT variance (wear, manufacturing tolerance,
etc.) -- a real problem, not always fixable by buying new matched motors.

This is conceptually DIFFERENT from what DRIVE_HEADING_kP fixes:
  - DRIVE_HEADING_kP = DYNAMIC correction, reacts loop-by-loop to drift as it
    happens (handles wheel slip, momentary unevenness, variable stuff).
  - Motor power imbalance = STATIC, structural fact about this exact robot
    that's the same every single run. Making a dynamic PID term constantly
    re-fight a constant bias is wasteful and likely leaves persistent small
    wobble even after otherwise-good tuning.

Proposed fix: separate CALIBRATION step (deterministic measurement -> a
constant), not a TUNING step (iterative search):

  1. Reset IMU heading to a known value.
  2. Drive straight open-loop (fixed, moderate power, e.g. 50% both sides,
     heading correction OFF) for a fixed distance, e.g. 48in.
  3. Measure ending heading vs starting heading -> heading_drift_degrees.
  4. Convert drift into a LEFT/RIGHT power trim multiplier pair:
       DRIVE_LEFT_TRIM  = 1.0 + (some function of drift)
       DRIVE_RIGHT_TRIM = 1.0 - (some function of drift)
     Exact formula needs real calibration data / experimentation -- concept
     is what matters here, not the precise math yet.
  5. Apply trims to raw left/right motor commands BEFORE the PID heading
     correction term even runs -- so open-loop the robot already wants to
     go straight, and DRIVE_HEADING_kP only has to clean up small residual/
     dynamic stuff, not fight a constant bias every loop. Likely reduces
     wobble and makes DRIVE_HEADING_kP itself easier/faster to tune too.
  6. Consider repeating the calibration test at a couple of different power
     levels (40/60/80%) since imbalance may not be linear across power range
     -- could reveal e.g. "these motors match fine at low power but diverge
     at high power," itself a useful diagnostic even if not corrected for.
  7. Also test the REVERSE direction separately (drive backward 48in) --
     imbalance need not be symmetric between forward and reverse.

Framing for the guide (if this gets written up): call this "drivetrain
balance CALIBRATION," explicitly distinct from "PID TUNING" -- calibration
= a one-time deterministic fact you measure about your specific hardware;
tuning = an iterative search for gains. Keeping this distinction sharp is
itself a good beginner-clarifying concept, independent of the auto-tuner idea.

---

## 11. DIAGNOSTIC VALUE BEYOND JUST OUTPUTTING NUMBERS

Side-thought: the tuner doesn't have to be a black box that just spits out
3 final numbers. It can DETECT problems a human doing hand-tuning would
naturally notice and flag them instead of silently compensating:

  - If turning +90 and turning -90 (or similar mirrored motions) consistently
    score very differently even after many iterations, that's likely a
    MECHANICAL asymmetry (weak/miswired motor on one side), not a tuning
    problem. A pure optimizer would just warp kP/kD asymmetrically to paper
    over it -- numbers "work" but the underlying fault is hidden, not fixed.
  - Better: have the tuner SURFACE this ("left turns consistently slower/
    weaker than right turns -- check your left motors") rather than silently
    absorbing it into the gains.
  - This turns the tool from "just an optimizer" into a genuine diagnostic
    aid, which fits the whole project's teaching mission much better than a
    black box.

---

## 12. OPEN QUESTIONS / NOT YET DECIDED
- Exact cost-function weights/thresholds for "how many degrees off is
  acceptable" beyond the confirmed 1deg dead-zone -- fine as-is, just noting
  it's a tunable-at-tune-time parameter per user's earlier point.
- Exact trim formula for section 10 (linear function of drift angle? needs
  real experimentation, not just theory).
- Whether kI should even be included in the automated search at all, given
  how consistently it converges near-zero in all precedent found so far --
  might be simpler and safer to exclude it from Twiddle entirely and only
  let the coarse classifier nudge it a little for the STEADY_STATE_OFFSET
  case, matching both this team's and the Udacity projects' real experience.
- Whether to build any of this for real, vs. keep it purely as a "going
  further" conceptual callout in the Explanation section without shipping
  actual autotune code in the base template (leaning toward the latter,
  consistent with the project's "keep beginner code simple" philosophy).
- Still waiting on user to potentially find documentation of an actual
  from-scratch VEX autotuner (not manual-flowchart libraries) to compare
  against everything above.
