# 74074Y Bamboozled — VEX V5 Drivetrain Coding Guide

A beginner-friendly teaching package for mentoring new programmers on a VEX
V5 team: a working, bug-fixed PID drivetrain template in C++, paired with a
from-scratch guide that takes a student with zero coding experience to a
functional autonomous robot.

## New student? Start here.

1. **Read the guide** — Google Doc (best for phones/Chromebooks): **[REPLACE WITH YOUR GOOGLE DOC SHARE LINK]**
   *(or read it on GitHub: [`docs/74074Y_Drivetrain_Guide.md`](docs/74074Y_Drivetrain_Guide.md))*
2. **Get the code** — [`templates/beginner/74074Y_Drivetrain_Template.cpp`](templates/beginner/74074Y_Drivetrain_Template.cpp). The guide's Part 1 walks you through pasting this into VEXcode step by step.
3. **Print or open the worksheet** once you get to tuning — [`archive/PID_Tuning_Log.docx`](archive/PID_Tuning_Log.docx).

Not sure which file in `docs/` you need? See [`docs/README.md`](docs/README.md).

## What's in here

| Folder | Contents |
| --- | --- |
| `templates/beginner/` | `74074Y_Drivetrain_Template.cpp` — the actual VEXcode V5 C++ file students paste into their project. Zones A–G, matches the guide step-for-step. |
| `docs/` | The guide and tuning log, each in `.docx` (source of truth, upload this to Google Docs) and `.md` (readable on GitHub) form. See `docs/README.md` for which one to open. |
| `brainstorm/` | `autotune_brainstorm.md` — exploratory notes on a possible future self-tuning PID add-on. **Not part of the current curriculum** — kept separate so it doesn't get mistaken for a finished feature. |

## Philosophy

- **Tutorial and Explanation are separate.** Students can get the robot
  moving first and understand *why* later, or read theory first — either
  path works because the two are never blended together.
- **Keep the base template simple.** Advanced ideas (slew rate limiting,
  odometry, self-tuning PID) are deliberately left out of the shipped code
  and mentioned only as "going further" callouts.

## Using the template

1. Open VEXcode V5, start a new C++ project.
2. Configure your motors + inertial sensor in the Devices menu (see the guide, Part 1, Step 2).
3. Paste `templates/beginner/74074Y_Drivetrain_Template.cpp` over `main.cpp`.
4. Follow the guide's Part 1 (Tutorial) to fill in Zone B with your robot's real measurements.

## Keeping the docx and Google Doc in sync

The Markdown files in `docs/` are the ones that render nicely on GitHub, but
the `.docx` files are the actual source for the Google Doc students read. If
you edit the guide:

1. Edit the `.docx` (or edit the `.md` and copy the changes over — your call).
2. Re-upload the `.docx` to Google Drive, replacing the existing file (or
   File → Open → Upload in Google Docs) so the share link stays the same.
3. If you edited the `.docx`, mirror the same change into the `.md` so the
   two don't drift apart. It's manual for now — fine at this scale.

## Versioning

Each season / robot iteration that needs a meaningfully different tuned
build should get a git tag (e.g. `v2025-worlds`) rather than a renamed copy
of the file — that's what version control is for.

## License

See `LICENSE`.
