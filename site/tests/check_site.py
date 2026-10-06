#!/usr/bin/env python3
"""Rebuild the site and check the result and the sources.

    python site/tests/check_site.py

Python 3 standard library only. Exits 0 when every check passes, 1 otherwise.

Checks, after a fresh build:
  - the build itself succeeds (this also verifies the vendored libraries)
  - every lesson source has complete front matter that matches its folder
  - page slugs are unique, and heading ids are unique inside each page
  - every internal link (#/slug and #/slug/heading) points to a real page and heading
  - links that cannot work from a single file (relative file paths) are flagged
  - every term in terms.tsv exists in the page data and its target resolves
  - every term link in a lesson has data behind it
  - the first-visit starting points exist
  - the output loads nothing from outside the file
"""
import json
import re
import subprocess
import sys
from html.parser import HTMLParser
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
SITE_DIR = TESTS_DIR.parent
REPO = SITE_DIR.parent
OUT = SITE_DIR / "out" / "index.html"

failures = []
warnings = []
passed = 0


def check(name, problems):
    """Record one named check. `problems` is a list of strings; empty means it passed."""
    global passed
    if problems:
        failures.append((name, problems))
        print("FAIL  " + name)
        for p in problems[:15]:
            print("        " + p)
        if len(problems) > 15:
            print("        ... and %d more" % (len(problems) - 15))
    else:
        passed += 1
        print("PASS  " + name)


# ---- 1. build ----

def run_build():
    result = subprocess.run([sys.executable, str(SITE_DIR / "build.py")],
                            capture_output=True, text=True, cwd=str(REPO))
    if result.returncode != 0:
        return ["build.py exited with code %d" % result.returncode] + \
               (result.stderr or result.stdout).strip().splitlines()
    if not OUT.is_file():
        return ["build.py ran but site/out/index.html does not exist"]
    return []


# ---- 2. front matter in the sources ----

FRONT = re.compile(r"\A---\n(.*?)\n---\n", re.S)


def read_front_matter(path):
    text = path.read_text(encoding="utf-8")
    m = FRONT.match(text)
    if not m:
        return None, text
    meta = {}
    for line in m.group(1).split("\n"):
        if line.strip():
            key, _, value = line.partition(":")
            meta[key.strip()] = value.strip()
    return meta, text[m.end():]


def lesson_sources():
    """(path, expected section or None for add-ons) for every file that should be a lesson."""
    sections = json.loads((REPO / "docs" / "sections.json").read_text(encoding="utf-8"))
    out = []
    for s in sections:
        folder = REPO / "docs" / s["slug"]
        if folder.is_dir():
            for path in sorted(folder.glob("*.md")):
                out.append((path, s["slug"]))
    for path in sorted((REPO / "addons").glob("*/README.md")):
        out.append((path, None))
    return sections, out


def check_front_matter():
    problems = []
    sections, sources = lesson_sources()
    known = {s["slug"] for s in sections}
    for path, folder_section in sources:
        rel = path.relative_to(REPO).as_posix()
        meta, body = read_front_matter(path)
        if meta is None:
            problems.append("%s: no front matter, so the build silently skips this file" % rel)
            continue
        for key in ("title", "section", "order", "terms"):
            if key not in meta:
                problems.append("%s: front matter is missing '%s'" % (rel, key))
        if not meta.get("title"):
            problems.append("%s: title is empty" % rel)
        if "order" in meta and not re.fullmatch(r"-?\d+", meta["order"]):
            problems.append("%s: order must be a whole number, got '%s'" % (rel, meta["order"]))
        if "terms" in meta and not (meta["terms"].startswith("[") and meta["terms"].endswith("]")):
            problems.append("%s: terms must be a list like [a, b] (use [] for none)" % rel)
        if meta.get("section") and meta["section"] not in known:
            problems.append("%s: section '%s' is not in docs/sections.json" % (rel, meta["section"]))
        if folder_section and meta.get("section") and meta["section"] != folder_section:
            problems.append("%s: section '%s' does not match its folder '%s'"
                            % (rel, meta["section"], folder_section))
        heading = re.search(r"^# (.+)$", body, re.M)
        if not heading:
            warnings.append("%s: no '# Title' line" % rel)
        elif meta.get("title") and heading.group(1).strip() != meta["title"]:
            warnings.append("%s: first heading '%s' differs from title '%s'"
                            % (rel, heading.group(1).strip(), meta["title"]))
    docs = REPO / "docs"
    for folder in sorted(p for p in docs.iterdir() if p.is_dir()):
        if folder.name not in known and any(folder.glob("*.md")):
            problems.append("docs/%s/ holds markdown but is not in docs/sections.json, so the build ignores it"
                            % folder.name)
    for s in sections:
        if not (docs / s["slug"]).is_dir():
            problems.append("docs/sections.json lists '%s' but docs/%s/ does not exist" % (s["slug"], s["slug"]))
    return problems


# ---- 3. the built page ----

class PageScan(HTMLParser):
    """Collect ids, links and term markers from one rendered lesson."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.ids = []
        self.hrefs = []
        self.term_keys = []
        self.bad_tags = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if "id" in a:
            self.ids.append(a["id"])
        if tag == "a" and "href" in a:
            self.hrefs.append(a["href"])
        if "data-term" in a:
            self.term_keys.append(a["data-term"])
        if tag in ("script", "iframe", "object", "embed", "form", "link", "style"):
            self.bad_tags.append(tag)


def load_data():
    html = OUT.read_text(encoding="utf-8")
    m = re.search(r'<script type="application/json" id="site-data">(.*?)</script>', html, re.S)
    if not m:
        raise SystemExit("could not find the site-data block in site/out/index.html")
    return html, json.loads(m.group(1))


def check_pages(data):
    problems_slugs, problems_ids, problems_links, problems_terms, problems_tags = [], [], [], [], []
    pages = {}
    for section in data["sections"]:
        for p in section["pages"]:
            if p["slug"] in pages:
                problems_slugs.append("duplicate slug: " + p["slug"])
            pages[p["slug"]] = p
            if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", p["slug"]):
                problems_slugs.append("slug has unusual characters: " + p["slug"])
    scans = {}
    for slug, p in pages.items():
        scan = PageScan()
        scan.feed(p["html"])
        scan.close()
        scans[slug] = scan
        seen = set()
        for i in scan.ids:
            if i in seen:
                problems_ids.append("%s: heading id '%s' appears twice" % (slug, i))
            seen.add(i)
        for tag in scan.bad_tags:
            problems_tags.append("%s: lesson HTML contains a <%s> tag" % (slug, tag))
    for slug, scan in scans.items():
        for href in scan.hrefs:
            if href.startswith("#/"):
                parts = href[2:].split("/", 1)
                target, heading = parts[0], (parts[1] if len(parts) > 1 else "")
                if target not in pages:
                    problems_links.append("%s: link %s points to a lesson that does not exist" % (slug, href))
                elif heading and heading not in scans[target].ids:
                    problems_links.append("%s: link %s points to a heading that does not exist" % (slug, href))
            elif re.match(r"(https?:|mailto:)", href, re.I):
                continue
            else:
                problems_links.append("%s: link '%s' cannot work inside a single file (use #/lesson-name or a full https link)"
                                      % (slug, href))
        for key in scan.term_keys:
            if key not in data["terms"]:
                problems_terms.append("%s: term link '%s' has no entry in the term data" % (slug, key))
    # terms.tsv against the data
    tsv = (REPO / "docs" / "reference" / "terms.tsv").read_text(encoding="utf-8").splitlines()[1:]
    wanted = [l.split("\t")[0].strip().lower() for l in tsv if l.strip()]
    for key in wanted:
        if key not in data["terms"]:
            problems_terms.append("terms.tsv term '%s' is missing from the built data" % key)
    for key, t in data["terms"].items():
        if t["slug"] not in pages:
            problems_terms.append("term '%s' points to a missing lesson '%s'" % (key, t["slug"]))
        elif t["id"] not in scans[t["slug"]].ids:
            problems_terms.append("term '%s' points to a missing heading %s#%s" % (key, t["slug"], t["id"]))
        if t["html"].strip() == "":
            problems_terms.append("term '%s' has an empty preview" % key)
    problems_start = ["starting point '%s' points to a missing lesson '%s'" % (s["id"], s["slug"])
                      for s in data["start"] if s["slug"] not in pages]
    if len(data["start"]) != 4:
        problems_start.append("expected 4 starting points, found %d" % len(data["start"]))
    empty = [s for s in data["sections"] if not s["pages"]]
    problems_sections = ["section '%s' has no lessons" % s["slug"] for s in empty]
    check("page slugs are unique and well formed", problems_slugs)
    check("heading ids are unique inside each lesson", problems_ids)
    check("no scripts, frames, forms or styles inside lesson HTML", problems_tags)
    check("every internal link and heading anchor resolves", problems_links)
    check("every term and term link has a valid target", problems_terms)
    check("first-visit starting points exist", problems_start)
    check("every section has at least one lesson", problems_sections)
    return pages


# ---- 4. nothing loads from outside ----

LOADERS = [
    ("src= that is not a data: URI", re.compile(r"""\bsrc\s*=\s*(?!["']?data:)""", re.I)),
    ("srcset=", re.compile(r"\bsrcset\s*=", re.I)),
    ("<link> tag", re.compile(r"<link\b", re.I)),
    ("<iframe>, <embed>, <object>, <img>, <video>, <audio>, <source>",
     re.compile(r"<(iframe|embed|object|img|video|audio|source)\b", re.I)),
    ("url(", re.compile(r"\burl\s*\(", re.I)),
    ("@import", re.compile(r"@import\b", re.I)),
    ("XMLHttpRequest", re.compile(r"XMLHttpRequest")),
    ("WebSocket", re.compile(r"\bnew\s+WebSocket\b")),
    ("sendBeacon", re.compile(r"sendBeacon")),
    ("dynamic import(", re.compile(r"(?<![.\w])import\s*\(")),
    ("fetch(", re.compile(r"(?<![.\w])fetch\s*\(")),
]
# MiniSearch's own map lookup is called fetch(): comment lines, calls on an
# object, and its method definition are not the network API.
FETCH_OK = re.compile(r"^\s*(\*|//|/\*)|\.fetch\(|^\s*fetch\(key, initial\) \{")


def check_offline(html):
    problems = []
    # lesson hyperlinks live inside the JSON data as escaped text, so they never match the tag patterns
    for name, pattern in LOADERS:
        for m in pattern.finditer(html):
            if name == "fetch(":
                start = html.rfind("\n", 0, m.start()) + 1
                end = html.find("\n", m.end())
                if FETCH_OK.search(html[start:end if end >= 0 else len(html)]):
                    continue
            problems.append("%s near: %s" % (name, html[max(0, m.start() - 30):m.end() + 30].replace("\n", " ")))
    # a plain external script tag would also load something
    for m in re.finditer(r"<script\b[^>]*>", html, re.I):
        if "src" in m.group(0).lower():
            problems.append("script tag with src: " + m.group(0))
    out_files = sorted(p.name for p in OUT.parent.iterdir())
    if out_files != ["index.html"]:
        problems.append("site/out should hold exactly index.html, found: " + ", ".join(out_files))
    check("output loads nothing from outside the file", problems)


def main():
    print("Rebuilding the site...")
    check("site builds (vendored libraries verified, term targets resolve)", run_build())
    if failures:
        print("\nThe build failed, so the remaining checks were skipped.")
        return 1
    check("lesson front matter is complete and matches folders", check_front_matter())
    html, data = load_data()
    pages = check_pages(data)
    check_offline(html)
    for w in warnings:
        print("WARN  " + w)
    print("\n%d checks passed, %d failed, %d warnings. %d lessons." % (passed, len(failures), len(warnings), len(pages)))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
