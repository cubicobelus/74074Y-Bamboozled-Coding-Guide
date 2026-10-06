# 74074Y Bamboozled VEX V5 Coding Guide

Read the site: https://cubicobelus.github.io/74074Y-Bamboozled-Coding-Guide/

A free pathway from zero coding knowledge to competition-level autonomous code for a VEX V5 robot. It comes from team 74074Y Bamboozled and is built from code the team has run in real competition. It is written for brand-new teams, whose members may have only used block coding or a little Python. Every piece of code is meant to come with a page that explains why it works.

> **Status: mid-rebuild.** The beginner template and the guide in this repo are the v1.0 release, and they still work. The new knowledge site, lessons and add-ons are being built. Most lesson pages are placeholders for now, and the add-ons, tools and intermediate template are not built yet. See [`ROADMAP.md`](ROADMAP.md) for what is done and what comes next.

## Start here

If you want what works today:

1. **Read the guide.** [`docs/74074Y_Drivetrain_Guide.md`](docs/74074Y_Drivetrain_Guide.md) reads fine right here on GitHub. It takes you from an empty project to a robot that drives and turns on its own.
2. **Get the code.** [`templates/beginner/74074Y_Drivetrain_Template.cpp`](templates/beginner/74074Y_Drivetrain_Template.cpp) is the file you paste into VEXcode V5. Start a new C++ project, add your motors and inertial sensor in the Devices menu, then paste the file over `main.cpp`. The guide's Part 1 walks through each step.
3. **Tune with the log.** When you reach tuning, use [`docs/PID_Tuning_Log.md`](docs/PID_Tuning_Log.md), or print the worksheet: [`archive/PID_Tuning_Log.docx`](archive/PID_Tuning_Log.docx).

## Where things are

| Folder | What is in it today |
| --- | --- |
| `addons/` | One folder for each planned add-on: autotuner, lift PID, MCL, distance sensor resets and balance calibration. Each has a placeholder README. There is no add-on code yet. |
| `archive/` | The original guide and tuning log as `.docx` files, for printing or uploading to Google Docs. |
| `brainstorm/` | Notes on a possible self-tuning PID add-on. Not part of the current curriculum. |
| `docs/` | The v1.0 guide and tuning log as `.md`, plus the pages of the new site, one folder per section. Most of those pages are placeholders. |
| `field/` | A placeholder for the shared field map: a README, a placeholder season file and a stub script. Nothing real yet. |
| `site/` | The build script and page shell that turn the pages in `docs/` and `addons/` into one HTML file, with its libraries and checks. |
| `templates/` | `beginner/` holds the v1.0 template. `intermediate/` holds only a README, because that template is not built yet. |
| `tools/` | Placeholders for the planned field simulator and interactive demos. Nothing is built yet. |

The top level also has `ROADMAP.md` and `LICENSE`.

## For coaches

This project is a pathway into programming, not a way to skip it. A team can't press a download button and end up with a finished robot program, and that is on purpose. The goal is that students can explain every line they run, change it, and fix it when it breaks. Use the guide to help students think, not to hand them finished code.

## Build and open the site locally

The site is built from the Markdown pages in this repo into one HTML file. A workflow rebuilds it and publishes it to the address above whenever `main` changes. To build it yourself you need Python 3.10 or newer and nothing else:

```
python site/build.py
```

Then open `site/out/index.html` in a browser. It works with no internet. `site/out/` is not committed, so you build it yourself. For how the build works, how to add a page and how to run the checks, see [`site/README.md`](site/README.md).

## Philosophy

- **Tutorial and Explanation are separate.** Students can get the robot
  moving first and understand *why* later, or read theory first — either
  path works because the two are never blended together.
- **Keep the base template simple.** Advanced ideas (slew rate limiting,
  odometry, self-tuning PID) are deliberately left out of the shipped code
  and mentioned only as "going further" callouts.

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
