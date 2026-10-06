# Site maintainer guide

This folder builds the knowledge site: one self-contained HTML file made from
the markdown lessons in `docs/` and the add-on pages in `addons/`. It shows one
lesson at a time, with a sidebar, search, a table of contents, copy buttons on
code, clickable vocabulary, a "Back to where you were" button and a first-visit
question. The file works when opened straight from disk with no internet.

## Build and open

You need Python 3.10 or newer. There is nothing to install: the libraries the
build uses are inside `site/vendor/`.

```
python site/build.py
```

This writes `site/out/index.html` and prints its size and a `file:///` address.
Open it by double-clicking the file, or paste that address into a browser.
`site/out/` is ignored by git, so the built file is never committed.

## Tests

Two scripts, both run from the repo root:

```
python site/tests/check_site.py
python site/tests/check_browser.py
```

- `check_site.py` rebuilds, then checks the sources and the output: front matter
  on every lesson, unique slugs and heading ids, every internal link and heading
  anchor, every term and its target, the first-visit starting points, and that
  nothing in the output loads from outside the file. It needs only Python.
- `check_browser.py` rebuilds, then opens the page in headless Microsoft Edge and
  clicks through it: routing, search, copy button, term panel, back button,
  first-visit card, phone width. If Edge is not found it says so and exits with
  code 2; set `EDGE_PATH` to the full path of `msedge.exe` if it is somewhere
  unusual. Its checks are written against the filler lessons (for example which
  lesson uses which term), so update the names and expected values in that file
  when real lessons replace the filler.

## Publishing

`.github/workflows/pages.yml` publishes the site to GitHub Pages at
https://cubicobelus.github.io/74074Y-Bamboozled-Coding-Guide/ every time `main` is
pushed. It can also be run by hand from the repo's Actions tab. In order, it:

1. checks out the repo and sets up Python;
2. runs `python site/build.py` and `python site/tests/check_site.py`. If either
   fails, nothing is deployed;
3. copies `site/out/index.html` into a folder of its own and uploads that folder
   as the Pages artifact;
4. deploys the artifact.

Only the one HTML file is published. The workflow uses only GitHub's own actions,
each pinned by its full commit SHA with the version in a comment. To update one,
find its newest release, look up the commit that release tag points to, and
replace both the SHA and the comment.

One setting is needed, once: in the repo's Settings, under Pages, set Source to
"GitHub Actions".

Two temporary things are on the published page until the lessons are written:

- **The banner** that says most lessons are placeholders. To remove it, delete the
  `wip-banner` line in `shell/page.html` and the `.wip-banner` rules at the end of
  `shell/style.css`.
- **The noindex tag**, `<meta name="robots" content="noindex">` in the head of
  `shell/page.html`. It asks search engines to skip the page. To allow indexing,
  delete that line. It takes effect on the next deploy, and search engines may need
  days or weeks to notice. Noindex is a request, not a lock: anyone with the link can
  still open the page.

## What is in `site/`

```
build.py          the build script (Python standard library only)
shell/
  page.html       the page skeleton: sidebar, content, panels, buttons
  style.css       all styling, using the colors defined at the top
  app.js          all behavior: routing, search, term panel, back stack, first-visit card
vendor/           third-party libraries, kept exactly as shipped
  markdown-it-py/  markdown rendering at build time (MIT)
  mdurl/           a dependency of markdown-it-py (MIT)
  minisearch/      search, runs in the page (MIT)
  HASHES.txt       SHA-256 of every vendored file, plus where each came from
tests/            check_site.py and check_browser.py
out/              build output (ignored by git)
```

The build fills `{{SITE_TITLE}}`, `{{STYLE}}`, `{{DATA}}`, `{{MINISEARCH}}` and
`{{APP}}` in `shell/page.html`. All lessons, term previews and the first-visit
choices go into the page as one block of JSON; the browser builds the search
index from it when the page loads.

## Where pages come from

1. `docs/sections.json` lists the sections: `slug`, `title`, `order`. It sets the
   order and names in the sidebar.
2. Every `docs/<section-slug>/*.md` file that starts with front matter is a lesson.
3. Every `addons/<name>/README.md` that starts with front matter is a page in
   whatever section its front matter names (the add-on stubs use `going-further`).

Files without front matter are ignored without any message: `docs/README.md`, the
v1 guide and tuning log, and the `tools/` READMEs are not pages. Folders under
`docs/` that are not listed in `sections.json` are ignored too. `check_site.py`
catches both mistakes for the folders it knows about.

## Lesson front matter

```
---
title: The 100-inch problem
section: learn-to-think
order: 1
terms: [error, tolerance]
---
# The 100-inch problem
```

| Field | Rule |
| --- | --- |
| `title` | Required. Shown in the sidebar, search results and the browser tab (`Title \| site name`). May contain colons. |
| `section` | Required. Must be a `slug` in `docs/sections.json`, and should match the folder the file is in. The build checks the first, `check_site.py` checks both. |
| `order` | Required, a whole number. Lessons are sorted by `order` inside a section; ties are broken by slug. |
| `terms` | Written on every lesson as a list (`[]` for none), and `check_site.py` requires it. The build and the page do not use it yet: terms are found by scanning the text, not by this list. |

The format is deliberately simple, and the parser is a few lines in `build.py`:
one `key: value` per line, lists written as `[a, b]`, no quotes, no multi-line
values. The file must begin with `---` on the very first line and have a closing
`---` line followed by a newline. If the opening or closing line is wrong, the file
has no front matter and is skipped silently.

**Slugs.** A lesson's slug is its file name without `.md`, so
`docs/tutorial/zones.md` is `#/zones`. An add-on page's slug is `addon-` plus its
folder name, so `addons/autotune/README.md` is `#/addon-autotune`. Slugs must be
unique across the whole site, and the build fails if two pages share one. Because
the slug is the link, renaming a file breaks every link to it.

**Links.** `#/slug` opens a lesson and `#/slug/heading-id` opens it at a heading.
A heading id is the heading text in lower case with every run of characters other
than letters and digits turned into `-`; a repeated heading gets `-2`, `-3` and so
on. Links to other websites are fine. Relative file links such as `other.md` cannot
work in a single file, and `check_site.py` flags them.

**Markdown.** Standard CommonMark plus tables and strikethrough. Raw HTML in a
lesson is not rendered; it shows as plain text. Fenced code blocks get a copy
button. Images only work as `data:` URIs, because anything else would have to be
fetched; an image with an ordinary path or web address fails the build.

## Clickable vocabulary: `docs/reference/terms.tsv`

Tab separated, with a header line `term`, `alternates`, `target`:

```
term	alternates	target
gear ratio	gear ratios|gearing	motors-count-degrees#gear-ratio
```

- `term` is the name shown in the preview panel. The lower-cased term is its key.
- `alternates` are other spellings, separated by `|`. Leave it empty for none.
- `target` is `lesson-slug#heading-id`: the section where the term is explained.

At build time every use of the term or an alternate in lesson text becomes a link
to its target, and the preview panel shows the real rendered section from that
heading down to the next heading of the same or higher level. The panel keeps the
first 6 blocks, so the opening lines of a term's section must work as a definition
on their own.

What the matching does and does not do:

- Whole words only, ignoring case. `error` does not match `errors` unless `errors`
  is listed as an alternate, and `heading-hold` or `heading_x` are not matches.
- The longest spelling wins (`gear ratio` before any shorter term).
- Terms are not linked inside headings, code (inline or fenced) or existing links.
  Terms inside list items and table cells are linked like any other text.
- A term is not linked inside its own definition section, including subsections.
- A term split across a line break in the markdown source is not matched.
- Two terms cannot share a spelling; the build fails if they do.
- The build fails if a target lesson or heading does not exist.

## How to add things

**A lesson.** Create `docs/<section>/<name>.md` with front matter, choose an
`order`, and write. Nothing else needs editing. Run `python site/tests/check_site.py`.

**A term.** Add a line to `docs/reference/terms.tsv`. Make sure the target heading
exists in the lesson (add it if not) and that its first lines are a standalone
definition. Rebuild: every use of the term across all lessons is linked
automatically.

**An add-on page.** Add `addons/<name>/README.md` with front matter (section
`going-further` unless there is a reason not to). Its slug will be `addon-<name>`.
Note that the build does not yet pull the add-on's code files into the page; the
overview plans that, and it is not built.

**A section.** Add it to `docs/sections.json` and create `docs/<slug>/`. A section
with no lessons fails `check_site.py` (the page itself still builds).

**The first-visit choices.** They are written in `START_PATHS` near the top of
`build.py`, not in a data file. The build fails if one of them points at a
lesson that does not exist.

## What the build checks, and when it fails

The build stops with `BUILD FAILED: ...` and a non-zero exit code when:

- a vendored file has the wrong hash, is missing, or an unlisted file sits in
  `vendor/` (see below);
- `docs/sections.json` or `terms.tsv` is malformed;
- a lesson's front matter lacks `title`, `section` or `order`, names an unknown
  section, or has a non-numeric `order`;
- two pages have the same slug;
- a term's target page or heading does not exist, or two terms share a spelling;
- a first-visit choice points at a missing lesson, or there are no pages at all;
- the output would load something from outside the file: `src=` that is not a
  `data:` URI, `<link>` tags, `url(`, `@import`, `fetch(`, `XMLHttpRequest`, or
  `import(`. This is checked on every lesson, every term preview and the page
  shell. Ordinary hyperlinks in lesson text are allowed.

The one exception to the `fetch(` rule is MiniSearch's own map lookup, which is
also called `fetch` and is not the network: comment lines, calls on an object,
and its method definition are let through, and nothing else.

What the build does not check, so `check_site.py` does: whether links inside
lessons point at real lessons and headings, whether a lesson's `section` matches
its folder, whether `terms` is present, whether a file silently lost its front
matter, and whether heading ids repeat.

## Vendored libraries

| Library | Version | Source |
| --- | --- | --- |
| markdown-it-py | 4.2.0 | pypi.org (wheel) |
| mdurl | 0.1.2 | pypi.org (wheel) |
| MiniSearch | 7.2.0 | npm (`dist/umd/index.js`, stored as `minisearch/index.js`) |

Files are kept exactly as shipped, with each library's license file. The exact
download URLs and the registry hashes are written in the header of
`vendor/HASHES.txt`.

**Verification.** Every build reads `vendor/HASHES.txt`, which lists a SHA-256 for
each vendored file, and fails if any file has a different hash, is missing, or if
a file under `vendor/` is not listed. So an edited or half-updated library cannot
build quietly. (Python bytecode folders are ignored, and the build does not write
them.)

**Updating a library.**

1. Look up the new version on pypi.org or npm and note the registry's published
   hash for the exact file.
2. Download that file into an empty temporary folder outside the repo and compare
   its hash with the registry's. Stop if they differ.
3. Replace the library's folder inside `vendor/` with the new files (for
   markdown-it-py: the `markdown_it/` package folder plus its license files; for
   mdurl: `mdurl/` plus `LICENSE`; for MiniSearch: `dist/umd/index.js` and
   `LICENSE.txt`). Do not edit any of them.
4. Update the version, URL and registry hash comments at the top of `HASHES.txt`.
5. Regenerate the hash lines, keeping the comment lines, from the repo root:

   ```python
   import hashlib, pathlib
   root = pathlib.Path("site/vendor")
   keep = [l for l in (root / "HASHES.txt").read_text().splitlines() if l.startswith("#")]
   files = sorted((p for p in root.rglob("*") if p.is_file()
                   and p.name != "HASHES.txt" and "__pycache__" not in p.parts),
                  key=lambda p: p.relative_to(root).as_posix())
   lines = ["%s  %s" % (hashlib.sha256(p.read_bytes()).hexdigest(), p.relative_to(root).as_posix())
            for p in files]
   (root / "HASHES.txt").write_text("\n".join(keep + lines) + "\n", newline="\n")
   ```

6. Run both test scripts. A new MiniSearch release may need the `fetch(` exception
   in `build.py` revisited, and a new markdown-it-py may change the rendered HTML.

The repo's `.gitattributes` stores text files with LF line endings. The hashes are
of those LF files, so do not vendor a file with Windows line endings.

## Known limits

- Without JavaScript the page shows only a notice. All lessons are rendered by
  the page's script from data embedded in the file.
- Everything is in one file, and each term preview repeats its section's HTML, so
  the file grows with the number of lessons and terms. The browser builds the search
  index for every lesson each time the page loads.
- The "Back to where you were" history lives in memory only. A reload clears it.
- The first-visit answer is stored in the browser's local storage. If storage is
  blocked the page still works, but the card shows again on the next bare visit.
- The preview panel opens on click or Enter, not on hover.
- The site title is a constant (`SITE_TITLE`) in `build.py`; the overview lists the
  final name as an open decision.
- The published page is temporary in two ways: it is marked noindex and carries a
  work-in-progress banner. See Publishing for how to remove both.
- Add-on pages are text only for now; they do not include the add-on's code files.
- `check_browser.py` needs Microsoft Edge, and its expectations are tied to the
  filler lessons.
