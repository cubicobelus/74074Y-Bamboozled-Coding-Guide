#!/usr/bin/env python3
"""Build the knowledge site into one self-contained HTML file.

    python site/build.py

Writes site/out/index.html. Needs only Python 3 and the files in site/vendor/.
"""
import hashlib
import json
import os
import re
import sys
from pathlib import Path

sys.dont_write_bytecode = True

SITE_DIR = Path(__file__).resolve().parent
REPO = SITE_DIR.parent
VENDOR = SITE_DIR / "vendor"
SHELL = SITE_DIR / "shell"
OUT = SITE_DIR / "out" / "index.html"

SITE_TITLE = "74074Y Bamboozled Coding Guide"

# First-visit question: (id, label, lesson slug). A slug of None means the
# first lesson of the section named in FIRST_OF.
START_PATHS = [
    ("new", "I am brand new to coding", "teaching-approach"),
    ("coded", "I have coded before", None),
    ("experienced", "I am experienced in coding", "intermediate-template"),
    ("coach", "I am a coach or mentor", "for-coaches"),
]
FIRST_OF = {"coded": "learn-to-think"}


class BuildError(Exception):
    pass


# ---- 1. vendor verification ----

def verify_vendor():
    listing = VENDOR / "HASHES.txt"
    if not listing.is_file():
        raise BuildError("site/vendor/HASHES.txt is missing")
    expected = {}
    for line in listing.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        digest, _, rel = line.partition("  ")
        expected[rel.strip()] = digest.strip()
    if not expected:
        raise BuildError("site/vendor/HASHES.txt lists no files")
    for rel, digest in expected.items():
        path = VENDOR / rel
        if not path.is_file():
            raise BuildError("vendored file is missing: " + rel)
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != digest:
            raise BuildError("hash mismatch for vendor/%s\n  expected %s\n  actual   %s"
                             % (rel, digest, actual))
    present = set()
    for dirpath, dirnames, filenames in os.walk(VENDOR):
        dirnames[:] = [d for d in dirnames if d != "__pycache__"]
        for name in filenames:
            rel = Path(dirpath, name).relative_to(VENDOR).as_posix()
            if rel != "HASHES.txt":
                present.add(rel)
    extra = sorted(present - set(expected))
    if extra:
        raise BuildError("files under vendor/ that HASHES.txt does not list: " + ", ".join(extra))
    return len(expected)


def load_markdown_it():
    sys.path.insert(0, str(VENDOR / "markdown-it-py"))
    sys.path.insert(0, str(VENDOR / "mdurl"))
    from markdown_it import MarkdownIt  # noqa: E402
    from markdown_it.token import Token  # noqa: E402
    return MarkdownIt, Token


# ---- 2. pages ----

FRONT = re.compile(r"\A---\n(.*?)\n---\n", re.S)


def parse_front_matter(text):
    m = FRONT.match(text)
    if not m:
        return None, text
    meta = {}
    for line in m.group(1).split("\n"):
        if not line.strip():
            continue
        key, _, value = line.partition(":")
        value = value.strip()
        if value.startswith("[") and value.endswith("]"):
            value = [v.strip() for v in value[1:-1].split(",") if v.strip()]
        meta[key.strip()] = value
    return meta, text[m.end():]


def read_text(path):
    return path.read_text(encoding="utf-8")


def collect_pages(sections):
    """Return a list of (slug, source path, meta, body)."""
    found = []
    section_slugs = {s["slug"] for s in sections}

    def add(slug, path):
        meta, body = parse_front_matter(read_text(path))
        if meta is None:
            return
        for key in ("title", "section", "order"):
            if key not in meta:
                raise BuildError("%s: front matter is missing '%s'" % (path.relative_to(REPO), key))
        if meta["section"] not in section_slugs:
            raise BuildError("%s: unknown section '%s'" % (path.relative_to(REPO), meta["section"]))
        try:
            meta["order"] = int(meta["order"])
        except ValueError:
            raise BuildError("%s: order must be a number" % path.relative_to(REPO))
        found.append((slug, path, meta, body))

    for section in sections:
        folder = REPO / "docs" / section["slug"]
        if folder.is_dir():
            for path in sorted(folder.glob("*.md")):
                add(path.stem, path)
    addons = REPO / "addons"
    if addons.is_dir():
        for path in sorted(addons.glob("*/README.md")):
            add("addon-" + path.parent.name, path)

    seen = {}
    for slug, path, _, _ in found:
        if slug in seen:
            raise BuildError("duplicate page slug '%s': %s and %s"
                             % (slug, seen[slug].relative_to(REPO), path.relative_to(REPO)))
        seen[slug] = path
    return found


# ---- 3. markdown ----

def slugify(text):
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return s or "section"


def make_renderer(MarkdownIt):
    md = MarkdownIt("commonmark", {"html": False}).enable(["table", "strikethrough"])

    def render_fence(self, tokens, idx, options, env):
        token = tokens[idx]
        lang = token.info.strip().split(" ")[0] if token.info else ""
        cls = ' class="language-%s"' % md.utils.escapeHtml(lang) if lang else ""
        return ('<div class="codeblock"><button class="copy" type="button">Copy</button>'
                "<pre><code%s>%s</code></pre></div>\n"
                % (cls, md.utils.escapeHtml(token.content)))

    def render_code_block(self, tokens, idx, options, env):
        return ('<div class="codeblock"><button class="copy" type="button">Copy</button>'
                "<pre><code>%s</code></pre></div>\n" % md.utils.escapeHtml(tokens[idx].content))

    md.add_render_rule("fence", render_fence)
    md.add_render_rule("code_block", render_code_block)
    return md


def inline_text(token):
    parts = []
    for child in token.children or []:
        if child.type in ("text", "code_inline"):
            parts.append(child.content)
        elif child.type in ("softbreak", "hardbreak"):
            parts.append(" ")
    return "".join(parts)


def render_page(md, body, linker, slug, want):
    """Render one page. `want` is the set of heading ids whose section HTML is also returned."""
    tokens = md.parse(body)
    used = set()
    toc = []
    plain = []
    stack = []  # (level, heading id) of the headings that contain the current text
    for i, tok in enumerate(tokens):
        if tok.type == "heading_open":
            text = inline_text(tokens[i + 1])
            base = slugify(text)
            hid, n = base, 2
            while hid in used:
                hid = "%s-%d" % (base, n)
                n += 1
            used.add(hid)
            tok.attrSet("id", hid)
            level = int(tok.tag[1])
            while stack and stack[-1][0] >= level:
                stack.pop()
            stack.append((level, hid))
            if level in (2, 3):
                toc.append({"id": hid, "text": text, "level": level})
        elif tok.type == "inline":
            plain.append(tok.content)
            if tokens[i - 1].type != "heading_open":
                linker.link_inline(tok, slug, {h for _, h in stack})
        elif tok.type in ("fence", "code_block"):
            plain.append(tok.content)
    html = md.renderer.render(tokens, md.options, {})
    sections = {}
    for i, tok in enumerate(tokens):
        if tok.type == "heading_open" and tok.attrGet("id") in want:
            level = int(tok.tag[1])
            end = len(tokens)
            for j in range(i + 1, len(tokens)):
                if tokens[j].type == "heading_open" and int(tokens[j].tag[1]) <= level:
                    end = j
                    break
            part = md.renderer.render(tokens[i:end], md.options, {})
            # the lesson already uses these ids, so the preview copy must not repeat them
            sections[tok.attrGet("id")] = re.sub(r' id="[^"]*"', "", part)
    return html, toc, re.sub(r"\s+", " ", " ".join(plain)).strip(), sections


# ---- 3b. vocabulary ----

def load_terms(path):
    """Read terms.tsv: term, alternate spellings (separated by |), target slug#heading-id."""
    lines = read_text(path).splitlines()
    if not lines or not lines[0].startswith("term\t"):
        raise BuildError("%s: first line must be the header 'term<TAB>alternates<TAB>target'"
                         % path.relative_to(REPO))
    terms = []
    for n, line in enumerate(lines[1:], 2):
        if not line.strip():
            continue
        cols = [c.strip() for c in line.split("\t")]
        if len(cols) != 3 or not cols[0] or "#" not in cols[2]:
            raise BuildError("%s line %d: expected term, alternates, slug#heading-id"
                             % (path.relative_to(REPO), n))
        slug, _, hid = cols[2].partition("#")
        names = [cols[0]] + [a.strip() for a in cols[1].split("|") if a.strip()]
        terms.append({"key": cols[0].lower(), "term": cols[0], "names": names, "slug": slug, "id": hid})
    return terms


class Linker:
    def __init__(self, terms, Token, escape):
        self.Token = Token
        self.escape = escape
        self.by_name = {}
        for t in terms:
            for name in t["names"]:
                k = re.sub(r"\s+", " ", name.lower())
                if k in self.by_name and self.by_name[k] is not t:
                    raise BuildError("the spelling '%s' belongs to two terms" % name)
                self.by_name[k] = t
        names = sorted(self.by_name, key=len, reverse=True)
        pattern = "|".join(re.escape(n).replace("\\ ", r"\s+") for n in names)
        # whole words only: not glued to letters, digits, "_" or "-"
        self.regex = re.compile(r"(?<![\w-])(?:%s)(?![\w-])" % pattern, re.I) if names else None

    def _text(self, content):
        tok = self.Token("text", "", 0)
        tok.content = content
        return tok

    def _html(self, content):
        tok = self.Token("html_inline", "", 0)
        tok.content = content
        return tok

    def link_inline(self, inline, slug, open_ids):
        """Wrap every use of a term in a link, except inside links and the term's own section."""
        if not self.regex or not inline.children:
            return
        depth = 0
        out = []
        for child in inline.children:
            if child.type == "link_open":
                depth += 1
            elif child.type == "link_close":
                depth -= 1
            if child.type != "text" or depth:
                out.append(child)
                continue
            text, pos = child.content, 0
            for m in self.regex.finditer(text):
                t = self.by_name[re.sub(r"\s+", " ", m.group(0).lower())]
                if t["slug"] == slug and t["id"] in open_ids:
                    continue
                if m.start() > pos:
                    out.append(self._text(text[pos:m.start()]))
                out.append(self._html('<a class="term" href="#/%s/%s" data-term="%s">'
                                      % (t["slug"], t["id"], self.escape(t["key"]))))
                out.append(self._text(m.group(0)))
                out.append(self._html("</a>"))
                pos = m.end()
            if pos == 0:
                out.append(child)
            elif pos < len(text):
                out.append(self._text(text[pos:]))
        inline.children = out


# ---- 4. assembling ----

def json_for_script(obj):
    # ASCII only, and no raw "<", so nothing inside can close the script tag.
    return json.dumps(obj, ensure_ascii=True).replace("<", "\\u003c")


def fill(template, values):
    return re.sub(r"\{\{(\w+)\}\}", lambda m: values[m.group(1)], template)


# ---- 5. check that nothing in the output loads a resource ----

# Things that load a resource. Plain hyperlinks in prose are allowed.
FORBIDDEN = [
    ("src= (only data: URIs are allowed)", re.compile(r"""\bsrc\s*=\s*(?!["']?data:)""", re.I)),
    ("stylesheet link", re.compile(r"""<link\b[^>]*>""", re.I)),
    ("url(", re.compile(r"\burl\s*\(", re.I)),
    ("@import", re.compile(r"@import\b", re.I)),
    ("fetch(", re.compile(r"(?<![.\w])fetch\s*\(")),
    ("XMLHttpRequest", re.compile(r"XMLHttpRequest")),
    ("import(", re.compile(r"(?<![.\w])import\s*\(")),
]

# MiniSearch has its own SearchableMap.fetch(key, initial) method. It looks
# a key up in a map and never touches the network. These are the only lines
# the check lets through: comment lines, calls on an object (`this._index.fetch(`),
# and the method definition itself.
ALLOWED_FETCH_LINE = re.compile(r"""^\s*(\*|//|/\*)|\.fetch\(|^\s*fetch\(key, initial\) \{""")


def check_text(label, text, problems):
    for name, pattern in FORBIDDEN:
        for m in pattern.finditer(text):
            if name == "fetch(":
                start = text.rfind("\n", 0, m.start()) + 1
                end = text.find("\n", m.end())
                line = text[start:end if end >= 0 else len(text)]
                if ALLOWED_FETCH_LINE.search(line):
                    continue
            if name == "stylesheet link" and "stylesheet" not in m.group(0).lower():
                continue
            problems.append("%s: found %s near: %s" % (label, name, text[max(0, m.start() - 30):m.end() + 30].replace("\n", " ")))


def main():
    count = verify_vendor()
    print("Vendor check passed (%d files match HASHES.txt)." % count)
    MarkdownIt, Token = load_markdown_it()
    md = make_renderer(MarkdownIt)
    terms = load_terms(REPO / "docs" / "reference" / "terms.tsv")
    linker = Linker(terms, Token, md.utils.escapeHtml)

    sections = json.loads(read_text(REPO / "docs" / "sections.json"))
    sections.sort(key=lambda s: s["order"])
    found = collect_pages(sections)

    problems = []
    out_sections = []
    total = 0
    section_html = {}
    page_titles = {}
    for section in sections:
        entries = [f for f in found if f[2]["section"] == section["slug"]]
        entries.sort(key=lambda f: (f[2]["order"], f[0]))
        pages = []
        for slug, path, meta, body in entries:
            want = {t["id"] for t in terms if t["slug"] == slug}
            html, toc, plain, sections_html = render_page(md, body, linker, slug, want)
            for hid, part in sections_html.items():
                section_html[(slug, hid)] = part
                check_text("preview %s#%s" % (slug, hid), part, problems)
            page_titles[slug] = meta["title"]
            check_text("page " + slug, html, problems)
            pages.append({
                "slug": slug, "title": meta["title"], "section": section["slug"],
                "html": html, "toc": toc, "text": plain,
            })
            total += 1
        out_sections.append({"slug": section["slug"], "title": section["title"], "pages": pages})
    if total == 0:
        raise BuildError("no pages found")

    terms_out = {}
    for t in terms:
        if t["slug"] not in page_titles:
            raise BuildError("term '%s' points to a page that does not exist: %s" % (t["term"], t["slug"]))
        if (t["slug"], t["id"]) not in section_html:
            raise BuildError("term '%s' points to a heading that does not exist: %s#%s"
                             % (t["term"], t["slug"], t["id"]))
        terms_out[t["key"]] = {"term": t["term"], "slug": t["slug"], "id": t["id"],
                               "page": page_titles[t["slug"]], "html": section_html[(t["slug"], t["id"])]}

    start_out = []
    for sid, label, slug in START_PATHS:
        if slug is None:
            pages_in = [s for s in out_sections if s["slug"] == FIRST_OF[sid]][0]["pages"]
            if not pages_in:
                raise BuildError("section '%s' has no lessons for the '%s' starting point" % (FIRST_OF[sid], sid))
            slug = pages_in[0]["slug"]
        if slug not in page_titles:
            raise BuildError("starting point '%s' points to a missing lesson: %s" % (sid, slug))
        start_out.append({"id": sid, "label": label, "slug": slug, "title": page_titles[slug]})

    mini = read_text(VENDOR / "minisearch" / "index.js")
    mini = re.sub(r"^//# sourceMappingURL=.*$", "", mini, flags=re.M)  # build output only
    if "</script" in mini.lower():
        raise BuildError("vendored script contains a closing script tag")
    app = read_text(SHELL / "app.js")
    style = read_text(SHELL / "style.css")
    template = read_text(SHELL / "page.html")

    data = json_for_script({"siteTitle": SITE_TITLE, "sections": out_sections,
                            "terms": terms_out, "start": start_out})
    check_text("shell page.html", template, problems)
    check_text("shell app.js", app, problems)
    check_text("shell style.css", style, problems)
    check_text("MiniSearch", mini, problems)
    if problems:
        raise BuildError("the output would load outside resources:\n  " + "\n  ".join(problems))

    page = fill(template, {
        "SITE_TITLE": SITE_TITLE, "STYLE": style, "DATA": data, "MINISEARCH": mini, "APP": app,
    })
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(page, encoding="utf-8", newline="\n")

    size = OUT.stat().st_size
    print("Built %d pages in %d sections, %d terms." % (total, len(out_sections), len(terms_out)))
    print("Wrote %s (%.1f KB)." % (OUT.relative_to(REPO), size / 1024))
    print()
    print("To rebuild:  python site/build.py")
    print("To open:     double-click site/out/index.html, or paste this into a browser address bar:")
    print("             " + OUT.as_uri())


if __name__ == "__main__":
    try:
        main()
    except BuildError as err:
        print("BUILD FAILED: " + str(err), file=sys.stderr)
        sys.exit(1)
