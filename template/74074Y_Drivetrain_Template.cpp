/*----------------------------------------------------------------------------*/
/*                                                                            */
/*   74074Y BAMBOOZLED  -  VEX V5 PID DRIVETRAIN TEMPLATE  (C++)              */
/*                                                                            */
/*   A beginner-friendly competition template for a 6-motor drivetrain        */
/*   with an Inertial Sensor (IMU).                                           */
/*                                                                            */
/*   HOW TO USE THIS FILE                                                     */
/*     1. Open VEXcode V5 and start a NEW C++ project.                        */
/*     2. Use the DEVICES menu to create your motors and inertial sensor.     */
/*     3. Select everything in main.cpp and paste this file over it.          */
/*     4. Only edit the sections marked  <<< EDIT ME >>>                      */
/*                                                                            */
/*   Read the guide alongside this file. Zones A-G below match the guide.     */
/*                                                                            */
/*----------------------------------------------------------------------------*/


/*============================================================================*/
/*  ZONE A  -  VEXCODE DEVICE CONFIGURATION                                   */
/*                                                                            */
/*  You do NOT type anything here. VEXcode fills this block in for you when   */
/*  you add devices in the DEVICES menu. It is here so you can double-check   */
/*  your ports without leaving the code.                                      */
/*============================================================================*/

// ---- START VEXCODE CONFIGURED DEVICES ----
// Robot Configuration:
// [Name]         [Type]              [Port(s)]
// Controller1    controller          primary
// LeftFront      motor               1
// LeftMiddle     motor               2
// LeftBack       motor               3
// RightFront     motor               4
// RightMiddle    motor               5
// RightBack      motor               6
// Inertial1      inertial            20
// ---- END VEXCODE CONFIGURED DEVICES ----

#include "vex.h"
#include <cmath>

using namespace vex;

competition Competition;


/*============================================================================*/
/*  ZONE B  -  MOTORS & ROBOT MEASUREMENTS            <<< EDIT ME >>>         */
/*============================================================================*/

/* --- Motor groups ----------------------------------------------------------
   A motor_group lets you command three motors with one line of code, exactly
   like the three motors on one side of your drivetrain move together.
   Replace the names below with the names YOU typed in the DEVICES menu.      */

motor_group left_motors  = motor_group(LeftFront,  LeftMiddle,  LeftBack);
motor_group right_motors = motor_group(RightFront, RightMiddle, RightBack);

/* --- Inertial sensor -------------------------------------------------------
   This makes a nickname (IMU) for your inertial sensor so the rest of the
   code never has to care what you named it. Replace Inertial1 only.          */

inertial &IMU = Inertial1;

/* --- Robot measurements ----------------------------------------------------
   WHEEL_DIAMETER : the size printed on your wheels, in inches (2.75/3.25/4).
   GEAR_RATIO     : (teeth on the MOTOR gear) / (teeth on the WHEEL gear).
                    Example: 36t on the motors, 48t on the wheels
                             -> 36 / 48 = 0.75
                    Direct drive (no gears at all) -> 1.0                      */

const double WHEEL_DIAMETER = 3.25;
const double GEAR_RATIO     = 0.75;

const double PI_VALUE            = 3.14159265358979;
const double WHEEL_CIRCUMFERENCE = WHEEL_DIAMETER * PI_VALUE;

/* --- Optional subsystems ---------------------------------------------------
   Leave these as 0 if your robot is drivetrain-only. The code for them is
   skipped entirely by the compiler, so nothing breaks.
   Set to 1 ONLY after you have created the matching device in the DEVICES
   menu (a motor named Intake, and/or a 3-wire digital out named Piston).     */

#define HAS_INTAKE 0
#define HAS_PISTON 0


/*============================================================================*/
/*  ZONE C  -  TUNABLE PARAMETERS (PID & MORE)        <<< EDIT ME later >>>   */
/*                                                                            */
/*  These are STARTING VALUES for a typical 6-motor, 3.25" wheel, 36:48 robot.*/
/*  Get everything working first, THEN tune. The guide walks you through it.  */
/*============================================================================*/

/* --- drive_distance() gains ----------------------------------------------- */
double DRIVE_kP         = 0.260;   // how hard we push when far from the target
double DRIVE_kD         = 1.500;   // how hard we brake as we get close
double DRIVE_HEADING_kP = 2.000;   // how hard we fight sideways drift

/* --- turn_to_angle() gains ------------------------------------------------ */
double TURN_kP = 0.900;
double TURN_kD = 2.000;

/* --- "Close enough" and safety limits ------------------------------------- */
const double DRIVE_TOLERANCE_INCHES = 0.50;   // within this = we arrived
const int    DRIVE_SETTLE_MS        = 150;    // must stay there this long
const int    DRIVE_TIMEOUT_MS       = 4000;   // give up after this long

const double TURN_TOLERANCE_DEGREES = 1.50;
const int    TURN_SETTLE_MS         = 150;
const int    TURN_TIMEOUT_MS        = 2500;

/* --- Power limits (percent) ----------------------------------------------- */
const double DRIVE_MAX_POWER = 80;   // cap so the robot does not wheelie/slip
const double TURN_MAX_POWER  = 60;
const double MIN_MOVE_POWER  =  4;   // enough to beat friction near the target

const int LOOP_MS = 20;              // how often the PID loop runs

/* --- Driver control -------------------------------------------------------- */
bool      USE_ARCADE_DRIVE = true;   // true = arcade, false = tank
const int JOYSTICK_DEADBAND = 5;     // ignore tiny joystick noise


/*============================================================================*/
/*  ZONE D  -  MOVEMENT FUNCTIONS (the heart of the template)                 */
/*  You should not need to edit anything in Zone D.                           */
/*============================================================================*/

/* Keeps an angle in the range -180 .. +180 so the robot always takes the
   SHORT way around. Turning from 350 deg to 10 deg is +20, not -340.         */
double wrap_180(double angle) {
  while (angle >  180) angle -= 360;
  while (angle < -180) angle += 360;
  return angle;
}

/* Stops a number from growing past +/- limit. */
double clamp(double value, double limit) {
  if (value >  limit) return  limit;
  if (value < -limit) return -limit;
  return value;
}

/* Converts a distance you understand (inches) into what the motors count
   (their own rotation in degrees).

   inches / circumference  = how many times the WHEEL must spin
   x 360                   = wheel spin measured in degrees
   / GEAR_RATIO            = how far the MOTOR must spin to do that

   The last step is a DIVIDE. With 36t on the motor and 48t on the wheel
   (GEAR_RATIO 0.75) the motor has to spin MORE than the wheel, and
   1 / 0.75 = 1.333 does exactly that. Multiplying here is the single most
   common bug in a drivetrain template - it makes the robot come up short.    */
double inches_to_motor_degrees(double inches) {
  return (inches / WHEEL_CIRCUMFERENCE) * 360.0 / GEAR_RATIO;
}

/* Average of how far the two sides have rolled, in motor degrees. */
double drivetrain_position_degrees() {
  return (left_motors.position(degrees) + right_motors.position(degrees)) / 2.0;
}


/*----------------------------------------------------------------------------*/
/*  turn_to_angle(target_angle)                                               */
/*                                                                            */
/*  Spins the robot in place until it faces target_angle (0 - 359.9),         */
/*  measured like a compass: 0 = the way the robot started, 90 = right,       */
/*  180 = behind, 270 = left.                                                 */
/*----------------------------------------------------------------------------*/
void turn_to_angle(double target_angle) {

  // Measure the error ONCE before the loop, then start prev_error at that
  // same value. If prev_error started at 0 the very first derivative would
  // be a huge fake number and the robot would jerk on the first 20 ms.
  double error      = wrap_180(target_angle - IMU.heading(degrees));
  double prev_error = error;

  int settle_timer = 0;
  int total_timer  = 0;

  while (settle_timer < TURN_SETTLE_MS && total_timer < TURN_TIMEOUT_MS) {

    error = wrap_180(target_angle - IMU.heading(degrees));

    double derivative = error - prev_error;   // how fast the error is shrinking
    prev_error = error;

    double power = (error * TURN_kP) + (derivative * TURN_kD);
    power = clamp(power, TURN_MAX_POWER);

    // Nudge past friction if we are still outside tolerance but barely moving.
    if (std::fabs(error) > TURN_TOLERANCE_DEGREES &&
        std::fabs(power) < MIN_MOVE_POWER) {
      power = (power >= 0) ? MIN_MOVE_POWER : -MIN_MOVE_POWER;
    }

    // Positive power = turn RIGHT: left side forward, right side backward.
    left_motors.spin(forward,   power, percent);
    right_motors.spin(forward, -power, percent);

    if (std::fabs(error) < TURN_TOLERANCE_DEGREES) settle_timer += LOOP_MS;
    else                                           settle_timer  = 0;

    total_timer += LOOP_MS;
    wait(LOOP_MS, msec);
  }

  left_motors.stop(brake);
  right_motors.stop(brake);
}


/*----------------------------------------------------------------------------*/
/*  drive_distance(inches)                                                    */
/*                                                                            */
/*  Drives straight forward (positive) or backward (negative) a set number    */
/*  of inches, using the IMU to hold the heading it started at.               */
/*----------------------------------------------------------------------------*/
void drive_distance(double inches) {

  double target_degrees    = inches_to_motor_degrees(inches);
  double tolerance_degrees = inches_to_motor_degrees(DRIVE_TOLERANCE_INCHES);
  double start_heading     = IMU.heading(degrees);

  left_motors.resetPosition();
  right_motors.resetPosition();

  double error      = target_degrees;
  double prev_error = error;

  int settle_timer = 0;
  int total_timer  = 0;

  while (settle_timer < DRIVE_SETTLE_MS && total_timer < DRIVE_TIMEOUT_MS) {

    error = target_degrees - drivetrain_position_degrees();

    double derivative = error - prev_error;
    prev_error = error;

    double power = (error * DRIVE_kP) + (derivative * DRIVE_kD);
    power = clamp(power, DRIVE_MAX_POWER);

    if (std::fabs(error) > tolerance_degrees &&
        std::fabs(power) < MIN_MOVE_POWER) {
      power = (power >= 0) ? MIN_MOVE_POWER : -MIN_MOVE_POWER;
    }

    // ---- Stay pointed the same way we started -----------------------------
    // heading_error is positive when the robot has drifted LEFT of its start
    // heading, negative when it has drifted RIGHT.
    double heading_error = wrap_180(start_heading - IMU.heading(degrees));
    double correction    = heading_error * DRIVE_HEADING_kP;

    // NOTE ON DRIVING BACKWARD: this correction does NOT need to be flipped.
    // How fast a robot spins depends only on the DIFFERENCE between the two
    // sides (right minus left), never on whether both sides happen to be
    // going forward or backward. Here that difference is always -2*correction,
    // so the same sign steers correctly at power +60 and at power -60.
    // (Templates that call spin(reverse, ...) with a positive magnitude DO
    //  have to flip it - because reversing the direction flips the difference
    //  too. Keeping power signed avoids that trap entirely.)

    left_motors.spin(forward,  power + correction, percent);
    right_motors.spin(forward, power - correction, percent);

    if (std::fabs(error) < tolerance_degrees) settle_timer += LOOP_MS;
    else                                      settle_timer  = 0;

    total_timer += LOOP_MS;
    wait(LOOP_MS, msec);
  }

  left_motors.stop(brake);
  right_motors.stop(brake);
}


/*============================================================================*/
/*  ZONE E  -  AUTONOMOUS ROUTINES & SELECTOR         <<< EDIT ME >>>         */
/*                                                                            */
/*  These six routes do not score anything - they exist so you can see the    */
/*  robot move and check your tuning. Replace them with your real routes.     */
/*  Remember: one field tile is 24 inches.                                    */
/*============================================================================*/

// ---- Route 1: the simplest possible test -----------------------------------
void auton_drive_forward() {
  drive_distance(24);
}

// ---- Route 2: does the robot come back to where it started? ----------------
void auton_forward_and_back() {
  drive_distance(24);
  wait(300, msec);
  drive_distance(-24);
}

// ---- Route 3: square - the classic tuning test -----------------------------
//      If your robot ends where it started, facing the same way, your
//      drive AND turn tuning are both good.
void auton_square() {
  drive_distance(24);
  turn_to_angle(90);
  drive_distance(24);
  turn_to_angle(180);
  drive_distance(24);
  turn_to_angle(270);
  drive_distance(24);
  turn_to_angle(0);
}

// ---- Route 4: triangle - tests turns that are not multiples of 90 ----------
void auton_triangle() {
  drive_distance(24);
  turn_to_angle(120);
  drive_distance(24);
  turn_to_angle(240);
  drive_distance(24);
  turn_to_angle(0);
}

// ---- Route 5: spiral - each leg gets longer --------------------------------
void auton_spiral() {
  drive_distance(12);
  turn_to_angle(90);
  drive_distance(18);
  turn_to_angle(180);
  drive_distance(24);
  turn_to_angle(270);
  drive_distance(30);
  turn_to_angle(0);
}

// ---- Route 6: creative - mix it up -----------------------------------------
void auton_creative() {
  drive_distance(18);
  turn_to_angle(45);
  drive_distance(12);
  turn_to_angle(315);
  drive_distance(12);
  turn_to_angle(180);
  drive_distance(30);
  turn_to_angle(0);
}

/* --- The selector ----------------------------------------------------------
   All six routes are loaded onto the robot at once. Tap the Brain screen
   before the match to cycle through them.                                    */

const int NUM_AUTONS = 6;
int auton_selection  = 0;

const char *auton_names[NUM_AUTONS] = {
  "1. Drive Forward",
  "2. Forward and Back",
  "3. Square",
  "4. Triangle",
  "5. Spiral",
  "6. Creative"
};

void run_selected_auton() {
  switch (auton_selection) {
    case 0: auton_drive_forward();  break;
    case 1: auton_forward_and_back(); break;
    case 2: auton_square();         break;
    case 3: auton_triangle();       break;
    case 4: auton_spiral();         break;
    case 5: auton_creative();       break;
    default: auton_drive_forward(); break;
  }
}

void draw_selector_screen() {
  Brain.Screen.clearScreen();
  Brain.Screen.setCursor(1, 1);
  Brain.Screen.print("74074Y  -  AUTON SELECTOR");
  Brain.Screen.setCursor(3, 1);
  Brain.Screen.print("Selected:  %s", auton_names[auton_selection]);
  Brain.Screen.setCursor(5, 1);
  Brain.Screen.print("Tap the screen to change");
  Brain.Screen.setCursor(7, 1);
  Brain.Screen.print("Heading: %.1f deg", IMU.heading(degrees));
}


/*============================================================================*/
/*  ZONE F  -  DRIVER CONTROL & CONTROLLER LOGIC      <<< EDIT ME >>>         */
/*============================================================================*/

bool intake_on      = false;   // remembers the last thing the driver asked for
bool piston_extended = false;

/* Ignores tiny joystick readings so the robot does not creep on its own. */
int apply_deadband(int value) {
  if (value > -JOYSTICK_DEADBAND && value < JOYSTICK_DEADBAND) return 0;
  return value;
}

void update_controls() {

  // ---- Drivetrain ----------------------------------------------------------
  int left_power  = 0;
  int right_power = 0;

  if (USE_ARCADE_DRIVE) {
    // Arcade: Axis3 (left stick up/down) drives, Axis1 (right stick L/R) turns.
    int drive_input = apply_deadband(Controller1.Axis3.position());
    int turn_input  = apply_deadband(Controller1.Axis1.position());
    left_power  = drive_input + turn_input;
    right_power = drive_input - turn_input;
  } else {
    // Tank: each stick controls the side it is on.
    left_power  = apply_deadband(Controller1.Axis3.position());
    right_power = apply_deadband(Controller1.Axis2.position());
  }

  left_motors.spin(forward,  left_power,  percent);
  right_motors.spin(forward, right_power, percent);

  // ---- Intake --------------------------------------------------------------
#if HAS_INTAKE
  if (Controller1.ButtonR1.pressing())      intake_on = true;
  else if (Controller1.ButtonR2.pressing()) intake_on = false;

  if (intake_on) Intake.spin(forward, 100, percent);
  else           Intake.stop(coast);
#endif

  // ---- Piston --------------------------------------------------------------
#if HAS_PISTON
  if (Controller1.ButtonL1.pressing())      piston_extended = true;
  else if (Controller1.ButtonL2.pressing()) piston_extended = false;

  Piston.set(piston_extended);
#endif
}


/*============================================================================*/
/*  ZONE G  -  MAIN PROGRAM & COMPETITION TEMPLATE                            */
/*  You should not need to edit anything in Zone G.                           */
/*============================================================================*/

/* Runs once when the program starts, BEFORE the match begins. */
void pre_auton() {

  left_motors.setStopping(brake);
  right_motors.setStopping(brake);

  // Calibrating takes about 2 seconds. DO NOT touch or move the robot.
  Brain.Screen.clearScreen();
  Brain.Screen.setCursor(1, 1);
  Brain.Screen.print("Calibrating IMU - do not move the robot");

  IMU.calibrate();
  while (IMU.isCalibrating()) {
    wait(50, msec);
  }

  // Let the driver pick a route by tapping the screen, until the match starts.
  bool was_pressing = false;
  draw_selector_screen();

  while (!Competition.isEnabled()) {
    bool pressing = Brain.Screen.pressing();

    // Only react to a NEW tap, not to a finger held down.
    if (pressing && !was_pressing) {
      auton_selection = (auton_selection + 1) % NUM_AUTONS;
      draw_selector_screen();
    }
    was_pressing = pressing;

    wait(50, msec);
  }
}

/* Runs during the 15-second autonomous period. */
void autonomous() {
  Brain.Screen.clearScreen();
  Brain.Screen.setCursor(1, 1);
  Brain.Screen.print("AUTON: %s", auton_names[auton_selection]);

  run_selected_auton();
}

/* Runs during the driver-controlled period. */
void driver_control() {
  while (true) {
    update_controls();
    wait(LOOP_MS, msec);
  }
}

int main() {
  Competition.autonomous(autonomous);
  Competition.drivercontrol(driver_control);

  pre_auton();

  while (true) {
    wait(100, msec);
  }
}
