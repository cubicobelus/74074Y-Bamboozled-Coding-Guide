#!/usr/bin/env python3
"""Drive the built site in headless Edge and check how it behaves.

    python site/tests/check_browser.py

Python 3 standard library only. It rebuilds the site, starts the installed
Edge with no window, opens site/out/index.html from disk and clicks through it.
Exits 0 when everything passes, 1 when a check fails, 2 when Edge is not found.

If Edge is installed somewhere unusual, set EDGE_PATH to its full path first.

These checks use the filler lessons (which lessons use which terms, how long
the kP section is). When real lessons replace the filler, update the lesson
names and expected values in this file.
"""
import base64
import json
import os
import select
import shutil
import socket
import struct
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

SITE_DIR = Path(__file__).resolve().parent.parent
REPO = SITE_DIR.parent
OUT = SITE_DIR / "out" / "index.html"


# ---- find Edge ----

def find_edge():
    env = os.environ.get("EDGE_PATH")
    if env:
        return env if Path(env).is_file() else None
    candidates = []
    for var in ("ProgramFiles(x86)", "ProgramFiles", "LocalAppData"):
        base = os.environ.get(var)
        if base:
            candidates.append(Path(base) / "Microsoft" / "Edge" / "Application" / "msedge.exe")
    candidates.append(Path("/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge"))
    for c in candidates:
        if c.is_file():
            return str(c)
    for name in ("msedge", "microsoft-edge", "microsoft-edge-stable"):
        found = shutil.which(name)
        if found:
            return found
    return None


# ---- a very small WebSocket client (enough for the DevTools protocol) ----

class WebSocket:
    def __init__(self, url):
        rest = url[len("ws://"):]
        hostport, _, path = rest.partition("/")
        host, _, port = hostport.partition(":")
        self.sock = socket.create_connection((host, int(port)), timeout=15)
        key = base64.b64encode(os.urandom(16)).decode()
        self.sock.sendall(("GET /%s HTTP/1.1\r\nHost: %s\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n"
                           "Sec-WebSocket-Key: %s\r\nSec-WebSocket-Version: 13\r\n\r\n"
                           % (path, hostport, key)).encode())
        buf = b""
        while b"\r\n\r\n" not in buf:
            chunk = self.sock.recv(4096)
            if not chunk:
                raise RuntimeError("the browser closed the connection during the handshake")
            buf += chunk
        head, _, self.buf = buf.partition(b"\r\n\r\n")
        if b" 101 " not in head.split(b"\r\n")[0]:
            raise RuntimeError("WebSocket handshake failed: " + head.split(b"\r\n")[0].decode(errors="replace"))

    def _need(self, n):
        while len(self.buf) < n:
            chunk = self.sock.recv(65536)
            if not chunk:
                raise RuntimeError("the browser closed the connection")
            self.buf += chunk

    def _take(self, n):
        self._need(n)
        data, self.buf = self.buf[:n], self.buf[n:]
        return data

    def send(self, text, opcode=0x1):
        data = text.encode() if isinstance(text, str) else text
        n = len(data)
        header = bytearray([0x80 | opcode])
        if n < 126:
            header.append(0x80 | n)
        elif n < 65536:
            header.append(0x80 | 126)
            header += struct.pack(">H", n)
        else:
            header.append(0x80 | 127)
            header += struct.pack(">Q", n)
        mask = os.urandom(4)
        header += mask
        self.sock.sendall(bytes(header) + bytes(b ^ mask[i % 4] for i, b in enumerate(data)))

    def recv(self, timeout):
        """Return the next text message, or None if nothing arrives within `timeout` seconds."""
        message = b""
        while True:
            if not self.buf:
                ready, _, _ = select.select([self.sock], [], [], timeout)
                if not ready:
                    return None
            b1, b2 = self._take(2)
            opcode, length = b1 & 0x0F, b2 & 0x7F
            if length == 126:
                length = struct.unpack(">H", self._take(2))[0]
            elif length == 127:
                length = struct.unpack(">Q", self._take(8))[0]
            if b2 & 0x80:
                mask = self._take(4)
                payload = bytes(b ^ mask[i % 4] for i, b in enumerate(self._take(length)))
            else:
                payload = self._take(length)
            if opcode == 0x8:
                raise RuntimeError("the browser closed the connection")
            if opcode == 0x9:
                self.send(payload, 0xA)
                continue
            if opcode == 0xA:
                continue
            message += payload
            if b1 & 0x80:
                return message.decode("utf-8")


class Browser:
    def __init__(self, ws):
        self.ws = ws
        self.next_id = 0
        self.network = []
        self.errors = []

    def _event(self, msg):
        method = msg.get("method")
        if method == "Network.requestWillBeSent":
            self.network.append(msg["params"]["request"]["url"])
        elif method == "Runtime.exceptionThrown":
            d = msg["params"]["exceptionDetails"]
            self.errors.append(str((d.get("exception") or {}).get("description") or d.get("text")))
        elif method == "Runtime.consoleAPICalled" and msg["params"]["type"] == "error":
            self.errors.append("console.error")

    def call(self, method, params=None):
        self.next_id += 1
        mid = self.next_id
        self.ws.send(json.dumps({"id": mid, "method": method, "params": params or {}}))
        deadline = time.time() + 30
        while time.time() < deadline:
            raw = self.ws.recv(1.0)
            if raw is None:
                continue
            msg = json.loads(raw)
            if msg.get("id") == mid:
                return msg
            self._event(msg)
        raise RuntimeError("no answer from the browser for " + method)

    def pump(self, seconds):
        """Wait, while still collecting events."""
        end = time.time() + seconds
        while True:
            left = end - time.time()
            if left <= 0:
                return
            raw = self.ws.recv(left)
            if raw is not None:
                self._event(json.loads(raw))

    def ev(self, expression):
        msg = self.call("Runtime.evaluate", {"expression": expression, "awaitPromise": True, "returnByValue": True})
        result = msg.get("result", {})
        if "exceptionDetails" in result:
            return "EXC " + str((result["exceptionDetails"].get("exception") or {}).get("description"))
        return result.get("result", {}).get("value")


# ---- test helpers ----

passed = 0
failed = 0


def eq(name, got, want):
    global passed, failed
    if got == want:
        passed += 1
        print("PASS  " + name)
    else:
        failed += 1
        print("FAIL  %s\n        got  %r\n        want %r" % (name, got, want))


def main():
    edge = find_edge()
    if not edge:
        print("Microsoft Edge was not found, so the browser checks cannot run.\n"
              "Install Edge, or set EDGE_PATH to the full path of msedge.exe and try again.\n"
              "(The other test, python site/tests/check_site.py, does not need a browser.)")
        return 2

    print("Rebuilding the site...")
    built = subprocess.run([sys.executable, str(SITE_DIR / "build.py")], capture_output=True, text=True, cwd=str(REPO))
    if built.returncode != 0:
        print("The build failed:\n" + (built.stderr or built.stdout))
        return 1
    base = OUT.as_uri()

    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    profile = tempfile.mkdtemp(prefix="site-check-")
    proc = subprocess.Popen([edge, "--headless=new", "--disable-gpu", "--no-first-run", "--no-default-browser-check",
                             "--remote-debugging-port=%d" % port, "--user-data-dir=" + profile, "about:blank"],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        target = None
        for _ in range(80):
            try:
                with urllib.request.urlopen("http://127.0.0.1:%d/json" % port, timeout=2) as r:
                    pages = [t for t in json.load(r) if t.get("type") == "page"]
                if pages:
                    target = pages[0]
                    break
            except OSError:
                pass
            time.sleep(0.25)
        if not target:
            print("Edge started but did not open a debugging connection.")
            return 1
        b = Browser(WebSocket(target["webSocketDebuggerUrl"]))
        run_checks(b, base)
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
        shutil.rmtree(profile, ignore_errors=True)

    print("\n%d passed, %d failed." % (passed, failed))
    return 1 if failed else 0


def run_checks(b, base):
    ev = b.ev
    sleep = b.pump

    def load(frag, pre=None):
        b.call("Page.navigate", {"url": "about:blank"})
        sleep(0.1)
        ident = None
        if pre:
            ident = b.call("Page.addScriptToEvaluateOnNewDocument", {"source": pre})["result"]["identifier"]
        b.call("Page.navigate", {"url": base + frag})
        sleep(0.9)
        if ident:
            b.call("Page.removeScriptToEvaluateOnNewDocument", {"identifier": ident})

    def key(k, code, vk):
        for t in ("rawKeyDown", "keyUp"):
            b.call("Input.dispatchKeyEvent", {"type": t, "key": k, "code": code, "windowsVirtualKeyCode": vk})
        sleep(0.12)

    def terms_in(selector="#lesson a.term"):
        return ev("[...document.querySelectorAll(%s)].map(a=>a.dataset.term)" % json.dumps(selector))

    for method in ("Network.enable", "Runtime.enable", "Page.enable"):
        b.call(method)
    b.call("Emulation.setFocusEmulationEnabled", {"enabled": True})
    b.call("Emulation.setDeviceMetricsOverride", {"width": 1300, "height": 420, "deviceScaleFactor": 1, "mobile": False})
    b.call("Browser.grantPermissions", {"permissions": ["clipboardReadWrite", "clipboardSanitizedWrite"]})
    suffix = " | 74074Y Bamboozled Coding Guide"

    # ---- basic page behaviour ----
    load("")
    eq("bare address opens the first lesson", ev("location.hash"), "#/welcome")
    load("#/imu-scale-test")
    eq("tab title follows the lesson", ev("document.title"), "IMU scale test" + suffix)
    eq("lesson table of contents", ev("[...document.querySelectorAll('#toc a')].map(a=>a.getAttribute('href'))"),
       ["#/imu-scale-test/example-code"])
    load("#/addon-autotune")
    eq("add-on page opens", ev("document.title"), "Autotuner" + suffix)
    load("#/does-not-exist")
    eq("unknown link shows the not-found message", ev("document.querySelector('#lesson h1').textContent"),
       "We could not find that page")
    eq("not-found title", ev("document.title"), "Page not found" + suffix)

    # search, back and forward, reload, table of contents
    load("#/imu-scale-test")
    ev("(()=>{const i=document.getElementById('search-input');i.value='placeholder';i.dispatchEvent(new Event('input'));})()")
    sleep(0.2)
    eq("search finds the lesson", ev("[...document.querySelectorAll('#search-results .r-title')].map(e=>e.textContent)"),
       ["IMU scale test"])
    ev("document.querySelector('#search-results a').click()")
    sleep(0.3)
    eq("search result opens the lesson and closes the list",
       ev("[location.hash, document.getElementById('search-results').hidden]"), ["#/imu-scale-test", True])
    ev("location.hash='#/tolerance'"); sleep(0.2)
    ev("location.hash='#/the-100-inch-problem'"); sleep(0.2)
    ev("history.back()"); sleep(0.3)
    eq("browser back", ev("document.title"), "Tolerance" + suffix)
    ev("history.forward()"); sleep(0.3)
    eq("browser forward", ev("document.title"), "The 100-inch problem" + suffix)
    b.call("Page.navigate", {"url": base + "#/imu-scale-test"}); sleep(0.8)
    b.call("Page.reload"); sleep(1.0)
    eq("reload keeps the lesson", ev("document.title"), "IMU scale test" + suffix)
    ev("document.querySelector('#toc a').click()"); sleep(0.3)
    eq("table of contents link", ev("location.hash"), "#/imu-scale-test/example-code")

    # copy button with a real mouse click
    load("#/imu-scale-test")
    r = json.loads(ev("(()=>{const r=document.querySelector('.copy').getBoundingClientRect();return JSON.stringify({x:r.x+r.width/2,y:r.y+r.height/2})})()"))
    for t in ("mousePressed", "mouseReleased"):
        b.call("Input.dispatchMouseEvent", {"type": t, "x": r["x"], "y": r["y"], "button": "left", "clickCount": 1})
    sleep(0.4)
    eq("copy button label", ev("document.querySelector('.copy').textContent"), "Copied")
    eq("copy button puts the code on the clipboard",
       (ev("navigator.clipboard.readText().catch(e=>'ERR '+e.message)") or "").replace("\r\n", "\n"),
       "// Example code goes here.\nint placeholder = 0;\n")

    # ---- vocabulary links ----
    load("#/the-100-inch-problem")
    eq("terms linked on every use", terms_in(), ["error", "tolerance"])
    eq("term link target", ev("document.querySelector('#lesson a.term').getAttribute('href')"), "#/tolerance/error")
    load("#/tolerance")
    eq("no term links inside headings", ev("document.querySelectorAll('#lesson h1 a, #lesson h2 a, #lesson h3 a').length"), 0)
    eq("a term's own section is not self-linked", ev(
        "(()=>{const h=document.getElementById('what-is-tolerance');let n=h.nextElementSibling,c=0;"
        "while(n&&!/^H[12]$/.test(n.tagName)){c+=n.querySelectorAll('a.term[data-term=\"tolerance\"]').length;n=n.nextElementSibling}return c})()"), 0)
    eq("text outside that section is linked", ev("document.querySelectorAll('#lesson a.term[data-term=\"tolerance\"]').length >= 1"), True)
    load("#/imu-scale-test")
    eq("heading term linked in a list item", ev("[...document.querySelectorAll('#lesson li a.term')].map(a=>a.dataset.term)"), ["heading", "error"])
    eq("no term links inside code blocks", ev("document.querySelectorAll('#lesson pre a').length"), 0)
    load("#/slowing-down-and-overshoot")
    eq("alternate spelling kP is linked", ev("[...document.querySelectorAll('#lesson a.term')].map(a=>a.textContent+':'+a.dataset.term).join(',')"), "kP:kp,error:error")
    load("#/drive-distance-walkthrough")
    eq("multi-word term is linked", ev("[...document.querySelectorAll('#lesson a.term')].map(a=>a.textContent+':'+a.dataset.term).join(',')"),
       "gear ratio:gear ratio,heading:heading,error:error")

    # ---- preview panel ----
    load("#/the-100-inch-problem")
    ev("window.__opener = document.querySelector('#lesson a.term'); window.__opener.focus()")
    ev("window.__opener.click()"); sleep(0.2)
    eq("panel opens", ev("!document.getElementById('preview-backdrop').hidden"), True)
    eq("panel title", ev("document.getElementById('preview-title').textContent"), "error")
    eq("panel shows the section", ev("document.getElementById('preview-body').textContent.startsWith('Error')"), True)
    eq("focus moves into the panel", ev("document.activeElement.id"), "preview")
    eq("page behind the panel is inert", ev("document.querySelector('.layout').hasAttribute('inert')"), True)
    eq("preview repeats no ids from the lesson", ev("document.querySelectorAll('#preview-body [id]').length"), 0)
    eq("panel covers most of the screen", ev("(()=>{const r=document.getElementById('preview').getBoundingClientRect();return r.height/innerHeight>0.8&&r.width/innerWidth>0.7})()"), True)
    key("Escape", "Escape", 27)
    eq("Escape closes the panel", ev("document.getElementById('preview-backdrop').hidden"), True)
    eq("focus returns to the term", ev("document.activeElement === window.__opener"), True)
    eq("page is no longer inert", ev("document.querySelector('.layout').hasAttribute('inert')"), False)
    ev("window.__opener.click()"); sleep(0.15)
    ev("document.getElementById('preview-close').click()"); sleep(0.1)
    eq("Close button closes the panel", ev("document.getElementById('preview-backdrop').hidden"), True)
    ev("window.__opener.focus()"); key("Enter", "Enter", 13)
    eq("Enter on a term opens the panel", ev("!document.getElementById('preview-backdrop').hidden"), True)
    for _ in range(6):
        key("Tab", "Tab", 9)
    eq("Tab stays inside the panel", ev("document.getElementById('preview').contains(document.activeElement)"), True)
    key("Escape", "Escape", 27)
    load("#/slowing-down-and-overshoot")
    ev("[...document.querySelectorAll('#lesson a.term')].find(a=>a.dataset.term==='kp').click()"); sleep(0.15)
    eq("a long section is cut to the first blocks plus a note",
       ev("[document.getElementById('preview-body').children.length, document.querySelector('.preview-more').textContent]"),
       [7, "The explanation continues in the lesson."])
    key("Escape", "Escape", 27)

    # ---- jumps and the back button ----
    load("#/the-100-inch-problem")
    eq("back button hidden at the start", ev("document.getElementById('back-button').hidden"), True)
    ev("window.scrollTo(0, 25)")
    y_a = ev("Math.round(scrollY)")
    ev("document.querySelector('#lesson a.term').click()"); sleep(0.15)
    ev("document.getElementById('preview-body').click()"); sleep(0.3)
    eq("clicking the panel jumps to the exact heading", ev("location.hash"), "#/tolerance/error")
    eq("panel closes after the jump", ev("document.getElementById('preview-backdrop').hidden"), True)
    eq("the heading is at the top of the view", ev("Math.abs(document.getElementById('error').getBoundingClientRect().top) < 40"), True)
    eq("tab title follows the jump", ev("document.title"), "Tolerance" + suffix)
    eq("back button appears", ev("!document.getElementById('back-button').hidden"), True)
    eq("back button is big", ev("document.getElementById('back-button').getBoundingClientRect().height >= 40"), True)
    ev("location.hash='#/slowing-down-and-overshoot'"); sleep(0.25)
    ev("window.scrollTo(0, 60)")
    y_c = ev("Math.round(scrollY)")
    ev("[...document.querySelectorAll('#lesson a.term')].find(a=>a.dataset.term==='kp').click()"); sleep(0.15)
    ev("document.getElementById('preview-go').click()"); sleep(0.3)
    eq("Go button jumps", ev("location.hash"), "#/from-this-to-pid/kp")
    eq("stack depth is shown", ev("document.getElementById('back-count').textContent"), " (2)")
    ev("document.getElementById('back-button').click()"); sleep(0.3)
    eq("back 1: lesson", ev("location.hash"), "#/slowing-down-and-overshoot")
    eq("back 1: exact scroll position", ev("Math.round(scrollY)"), y_c)
    eq("back 1: one jump left to undo", ev("!document.getElementById('back-button').hidden"), True)
    ev("document.getElementById('back-button').click()"); sleep(0.3)
    eq("back 2: lesson", ev("location.hash"), "#/the-100-inch-problem")
    eq("back 2: exact scroll position", ev("Math.round(scrollY)"), y_a)
    eq("button hides when nothing is left", ev("document.getElementById('back-button').hidden"), True)
    load("#/tolerance")
    ev("window.scrollTo(0, 0)")
    ev("document.querySelector('#lesson a.term[data-term=\"tolerance\"]').click()"); sleep(0.15)
    ev("document.getElementById('preview-body').click()"); sleep(0.3)
    eq("a jump inside the same lesson goes to the heading", ev("location.hash"), "#/tolerance/what-is-tolerance")
    ev("document.getElementById('back-button').click()"); sleep(0.3)
    eq("back inside the same lesson restores the scroll", ev("Math.round(scrollY)"), 0)
    load("#/does-not-exist")
    eq("not-found page starts with no back entry", ev("document.getElementById('back-button').hidden"), True)
    load("#/the-100-inch-problem")
    ev("document.querySelector('#lesson a.term').setAttribute('data-term','zzz'); document.querySelector('#lesson a.term').click()")
    sleep(0.3)
    eq("a term with no data still works as a normal link", ev("location.hash"), "#/tolerance/error")

    # ---- first-visit question ----
    routes = [("new", "teaching-approach"), ("coded", "the-100-inch-problem"),
              ("experienced", "intermediate-template"), ("coach", "for-coaches")]
    load(""); ev("localStorage.clear()"); load("")
    eq("card shows on a first visit", ev("!document.getElementById('welcome-backdrop').hidden"), True)
    eq("card choices", ev("[...document.querySelectorAll('#welcome .c-label')].map(e=>e.textContent)"),
       ["I am brand new to coding", "I have coded before", "I am experienced in coding", "I am a coach or mentor"])
    eq("focus is in the card", ev("document.activeElement.id"), "welcome")
    for i, (name, slug) in enumerate(routes):
        load(""); ev("localStorage.clear()"); load("")
        ev("document.querySelectorAll('#welcome-choices .choice')[%d].click()" % i); sleep(0.3)
        eq("choice '%s' goes to %s" % (name, slug), ev("location.hash"), "#/" + slug)
        eq("choice '%s' is remembered" % name, ev("localStorage.getItem('bamboozled-start')"), name)
        eq("card closes after '%s'" % name, ev("document.getElementById('welcome-backdrop').hidden"), True)
    load("")
    eq("no card on the next bare visit", ev("document.getElementById('welcome-backdrop').hidden"), True)
    ev("document.getElementById('change-start').click()"); sleep(0.15)
    eq("'Change my starting point' reopens the card", ev("!document.getElementById('welcome-backdrop').hidden"), True)
    eq("the current answer is marked", ev("[...document.querySelectorAll('#welcome-choices .choice')].map(b=>b.getAttribute('aria-pressed')).join()"),
       "false,false,false,true")
    key("Escape", "Escape", 27)
    eq("Escape closes the card and keeps the answer", ev("[document.getElementById('welcome-backdrop').hidden, localStorage.getItem('bamboozled-start')]"), [True, "coach"])
    eq("focus returns to the control", ev("document.activeElement.id"), "change-start")
    ev("document.getElementById('change-start').click()"); sleep(0.1)
    ev("document.querySelectorAll('#welcome-choices .choice')[1].click()"); sleep(0.3)
    eq("the answer can be changed", ev("[location.hash, localStorage.getItem('bamboozled-start')]"), ["#/the-100-inch-problem", "coded"])
    load(""); ev("localStorage.clear()"); load("")
    ev("document.getElementById('welcome-skip').click()"); sleep(0.2)
    eq("skip closes the card and is remembered", ev("[document.getElementById('welcome-backdrop').hidden, localStorage.getItem('bamboozled-start')]"), [True, "skip"])
    load("")
    eq("after skip the card does not come back", ev("document.getElementById('welcome-backdrop').hidden"), True)
    load("#/odometry"); ev("localStorage.clear()"); load("#/odometry")
    eq("a direct lesson link never shows the card", ev("document.getElementById('welcome-backdrop').hidden"), True)
    block = "Object.defineProperty(window,'localStorage',{get(){throw new DOMException('blocked','SecurityError')}});"
    load("", block)
    eq("blocked storage: the card still shows", ev("!document.getElementById('welcome-backdrop').hidden"), True)
    ev("document.querySelectorAll('#welcome-choices .choice')[2].click()"); sleep(0.3)
    eq("blocked storage: the choice still routes", ev("location.hash"), "#/intermediate-template")

    # ---- phone-sized screen ----
    b.call("Emulation.setDeviceMetricsOverride", {"width": 390, "height": 760, "deviceScaleFactor": 2, "mobile": True})
    load("#/tolerance")
    eq("phone: no sideways scrolling", ev("document.documentElement.scrollWidth <= innerWidth + 1"), True)
    eq("phone: menu button is shown, sidebar hidden", ev("[getComputedStyle(document.querySelector('.topbar')).display !== 'none', getComputedStyle(document.getElementById('sidebar')).display]"), [True, "none"])
    ev("document.getElementById('menu-button').click()"); sleep(0.2)
    eq("phone: menu opens", ev("getComputedStyle(document.getElementById('sidebar')).display"), "block")
    b.call("Emulation.setDeviceMetricsOverride", {"width": 1300, "height": 420, "deviceScaleFactor": 1, "mobile": False})

    b.call("Page.navigate", {"url": "about:blank"})
    sleep(0.2)
    outside = [u for u in b.network if not u.startswith(base) and u != "about:blank"]
    eq("no network requests beyond the file itself", outside, [])
    eq("no script errors", b.errors, [])


if __name__ == "__main__":
    sys.exit(main())
