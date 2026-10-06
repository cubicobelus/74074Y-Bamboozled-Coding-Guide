# Roadmap

Build order and status of every piece. Updated October 6, 2026.

The order builds what brand-new teams need first, and never starts a piece
before the pieces it depends on. Physics (a robot pushing game elements around)
is the biggest scope risk, so the field planner ships without it.

## Build order

| # | Piece | Depends on | Status |
| --- | --- | --- | --- |
| 1 | Beginner template cleanup: fix the distance bug, add IMU scale correction, make the generic and 74074Y test robot versions, review pass | Nothing | Not started |
| 2 | Repo restructure and site skeleton | Nothing | Done (see below) |
| 3 | "Learn to think" chapters and the beginner tutorial | 1, 2 | Not started |
| 4 | First demos: PID playground and the 100-inch problem | 2 | Not started |
| 5 | Competition and consistency chapter | 2 | Not started |
| 6 | Intermediate template | 1 | Not started |
| 7 | Odometry and its chapter | 6 | Not started |
| 8 | Field definition and path planner (no physics) | 2 | Not started |
| 9 | MCL: rebuilt in the simulator first, then on the robot | 7, 8 | Not started |
| 10 | Stretch: physics, bezier paths, intermediate autotuner, balance calibration | Varies | Idea |

## What piece 2 covers

Done:

- The repo is sorted into templates, add-ons, field, docs, tools, brainstorm and
  archive. Every folder and every site page from the plan exists as a stub with
  filler text and no real lesson content.
- The old v1 template moved to `templates/beginner/` and the old `.docx` files
  moved to `archive/`. The v1.0 tag still points at the old layout.
- A build script (`python site/build.py`) turns the markdown lessons and add-on
  pages into one self-contained HTML file that works offline. The libraries it
  uses are vendored with licenses and checked against recorded hashes.
- The page has a sidebar, one lesson at a time, a link for every lesson, a tab
  title for every lesson, search, a table of contents, and copy buttons on code.
- Black and gold theme.
- Reading features, wired to a handful of filler terms: every use of a term is a
  clickable link, a large preview panel shows the start of the term's section, a
  "Back to where you were" button undoes jumps one at a time, and a first-visit
  question points readers to a starting lesson and can be changed later.
- Repeatable checks: `python site/tests/check_site.py` for the sources and the
  built file, and `python site/tests/check_browser.py` for behavior in a
  headless browser.
- A maintainer guide in `site/README.md`.

Not done yet in piece 2:

- Publishing. The site is not on GitHub Pages and there is no workflow that
  builds and publishes it.
- Add-on pages do not yet show the add-on's real code files with a copy button
  and download link.
- Release downloads (the beginner `.cpp` files and the intermediate `.zip`).
- The real vocabulary list. Only a few filler terms exist.
- All real lesson content.

## What exists today

The v1.0 beginner template, the old drivetrain guide, the PID tuning log, and
the autotuner brainstorm notes. The project overview describes beginner
paste-in versions of the autotuner and the lift PID as built, but their code is
not in this repo yet, so the add-on folders hold stubs only. Everything else in
the repo is a stub waiting for content.

## Decisions still open

- Site name and title shown at the top of every page.
- Name of the intermediate template's library folder: keep `Bambi-Template` or
  pick a public name.
- Which small libraries to bundle: settled for now (markdown-it-py at build
  time, MiniSearch for search).
- Motor commands in the intermediate template: percent or volts.
- Which add-ons get a beginner paste-in version.
- Odometry built into the intermediate template or shipped as an add-on.
- Which season's field to model first, and how detailed game elements need to be.
- Where the autotuner sits in the beginner selector, so it is never the route
  selected at power-on.
- The exact wording of VEX's Student-Centered Policy, to be quoted and linked from
  the current Game Manual.
- The wording of the first-visit question and the four starting paths.
- Whether the vocabulary panel is text only or can show a small diagram.
- The exact wording of the choose-one comments in the beginner template.
- Whether the built HTML file is committed or built by a workflow when publishing.
- Later option: one static page per lesson so search engines can index them.
