#!/usr/bin/env python3
"""
Folder Galaxy - a live 3D constellation of your folders and files.

* Reads only names, sizes and modification times - never file contents.
* Read-only: it never writes, moves or deletes anything.
* The page can switch to any folder, but only inside BROWSE_ROOT.
* Python standard library only: no dependencies to install.

Usage:
    python3 server.py                      # your home folder
    python3 server.py ~/projects --open    # a specific folder, opens the browser
    python3 server.py --help               # all options

Every option can also be set with an environment variable (see README).
"""
import argparse
import fnmatch
import json
import os
import queue
import sys
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

__version__ = "1.0.0"

STATIC_DIR = Path(__file__).resolve().parent / "static"
IDLE_STOP = 60  # seconds without open pages before a folder stops being watched

DEFAULT_EXCLUDE = (
    # development
    ".git,.hg,.svn,node_modules,venv,.venv,__pycache__,.mypy_cache,.pytest_cache,"
    ".ruff_cache,.idea,.vscode,.next,.nuxt,.tox,.gradle,.m2,site-packages,*.pyc,.DS_Store,"
    # heavy folders usually found in a home directory (Linux / macOS / Windows)
    ".cache,.npm,.nvm,.pyenv,.cargo,.rustup,.conda,miniconda3,anaconda3,snap,.docker,"
    ".vscode-server,.cursor-server,.local,.Trash,Library,AppData,$RECYCLE.BIN,"
    "System Volume Information"
)


def env(name, default=None):
    value = os.environ.get(name)
    return value if value not in (None, "") else default


def to_web(path):
    """Paths are always sent to the browser with forward slashes (also on Windows)."""
    return path.replace("\\", "/") if os.sep == "\\" else path


class Config:
    def __init__(self, root, browse_root, host, port, interval, max_nodes, exclude):
        self.root = root
        self.browse_root = browse_root
        self.host = host
        self.port = port
        self.interval = interval
        self.max_nodes = max_nodes
        self.exclude_names, self.exclude_globs = set(), []
        for item in (x.strip() for x in exclude.split(",")):
            if not item:
                continue
            if any(c in item for c in "*?["):
                self.exclude_globs.append(item)
            else:
                self.exclude_names.add(item)

    def excluded(self, name):
        return name in self.exclude_names or any(fnmatch.fnmatch(name, g) for g in self.exclude_globs)


CFG = None  # set in main()


def log(*args):
    print(time.strftime("%Y-%m-%d %H:%M:%S"), *args, flush=True)


def resolve_path(raw, cfg=None):
    """Path requested by the page -> (real path, None) or (None, error code).

    Only folders inside cfg.browse_root are allowed. Symlinks are resolved first,
    so a link pointing outside the allowed area is refused too.
    """
    cfg = cfg or CFG
    raw = (raw or "").strip() or cfg.root
    if raw == "~" or raw.startswith("~/") or raw.startswith("~\\"):
        raw = os.path.expanduser("~") + raw[1:]
    if not os.path.isabs(raw):
        raw = os.path.join(cfg.browse_root, raw)
    real = os.path.realpath(raw)
    try:
        inside = os.path.commonpath([real, cfg.browse_root]) == cfg.browse_root
    except ValueError:  # e.g. different drives on Windows
        inside = False
    if not inside:
        return None, "outside"
    if not os.path.isdir(real):
        return None, "missing"
    if not os.access(real, os.R_OK | os.X_OK):
        return None, "denied"
    return real, None


# --------------------------------------------------------------------------- #
# Scanning                                                                    #
# --------------------------------------------------------------------------- #
# Every node: id = path relative to the root ("" for the root), p = parent id,
# n = name, t = "d" folder / "f" file, s = bytes, m = last modified (epoch),
# f = number of files inside (folders only), e = 1 if the folder is unreadable.

def scan_tree(root, cfg=None):
    cfg = cfg or CFG
    try:
        root_mtime = int(os.stat(root).st_mtime)
    except OSError:
        root_mtime = 0
    name = os.path.basename(root.rstrip("/\\")) or to_web(root)
    nodes = {"": {"id": "", "p": None, "n": name, "t": "d", "s": 0, "m": root_mtime, "f": 0}}
    truncated = False
    stack = [("", root)]
    while stack and not truncated:
        rel, abs_dir = stack.pop()
        try:
            with os.scandir(abs_dir) as it:
                entries = list(it)
        except OSError:
            nodes[rel]["e"] = 1
            continue
        for e in entries:
            if cfg.excluded(e.name):
                continue
            if len(nodes) >= cfg.max_nodes:
                truncated = True
                break
            rid = e.name if rel == "" else rel + "/" + e.name
            try:
                st = e.stat(follow_symlinks=False)
                is_dir = e.is_dir(follow_symlinks=False)
            except OSError:
                continue
            if is_dir:
                nodes[rid] = {"id": rid, "p": rel, "n": e.name, "t": "d", "s": 0,
                              "m": int(st.st_mtime), "f": 0}
                stack.append((rid, e.path))
            else:
                nodes[rid] = {"id": rid, "p": rel, "n": e.name, "t": "f",
                              "s": st.st_size, "m": int(st.st_mtime)}

    # Roll sizes, file counts and latest modification up to every folder
    for node in list(nodes.values()):
        if node["t"] != "f":
            continue
        size, mtime, pid = node["s"], node["m"], node["p"]
        while pid is not None:
            parent = nodes.get(pid)
            if parent is None:
                break
            parent["s"] += size
            parent["f"] += 1
            if mtime > parent["m"]:
                parent["m"] = mtime
            pid = parent["p"]
    return nodes, truncated


def diff_trees(old, new):
    added = [new[k] for k in new.keys() - old.keys()]
    removed = list(old.keys() - new.keys())
    changed = []
    for k in new.keys() & old.keys():
        a, b = old[k], new[k]
        if a["s"] != b["s"] or a["m"] != b["m"] or a.get("f") != b.get("f") or a.get("e") != b.get("e"):
            changed.append(b)
    added.sort(key=lambda n: n["id"].count("/"))  # parents before children
    return added, removed, changed


# --------------------------------------------------------------------------- #
# One watcher per folder that is open in at least one page                   #
# --------------------------------------------------------------------------- #
class Watcher:
    def __init__(self, root):
        self.root = root
        self.lock = threading.Lock()
        self.subscribers = set()
        self.last_seen = time.time()
        started = time.time()
        self.nodes, self.truncated = scan_tree(root)
        self.scan_time = time.time() - started
        self.version = 1
        log(f"Watching {root}: {len(self.nodes)} items in {self.scan_time:.2f}s"
            + (" (MAX_NODES limit reached)" if self.truncated else ""))
        threading.Thread(target=self.loop, daemon=True).start()

    def snapshot_payload(self):
        return json.dumps({
            "v": self.version,
            "path": to_web(self.root),
            "root": self.nodes[""]["n"],
            "truncated": self.truncated,
            "maxNodes": CFG.max_nodes,
            "nodes": list(self.nodes.values()),
        }, separators=(",", ":"))

    def subscribe(self):
        q = queue.Queue(maxsize=200)
        with self.lock:
            q.put(("snapshot", self.snapshot_payload()))
            self.subscribers.add(q)
        return q

    def unsubscribe(self, q):
        with self.lock:
            self.subscribers.discard(q)
            self.last_seen = time.time()

    def publish(self, event, payload):
        for q in list(self.subscribers):
            try:
                q.put_nowait((event, payload))
            except queue.Full:  # page too slow: make it reconnect
                self.subscribers.discard(q)
                try:
                    q.put_nowait(("close", ""))
                except queue.Full:
                    pass

    def loop(self):
        while True:
            # huge folders are checked less often, to stay light on small machines
            time.sleep(max(CFG.interval, self.scan_time * 5))
            with self.lock:
                idle = not self.subscribers and time.time() - self.last_seen > IDLE_STOP
            if idle:
                with REGISTRY_LOCK:
                    if (REGISTRY.get(self.root) is self and not self.subscribers
                            and time.time() - self.last_seen > IDLE_STOP):
                        del REGISTRY[self.root]
                        log(f"Stopped watching {self.root} (no open pages)")
                        return
            try:
                started = time.time()
                new_nodes, truncated = scan_tree(self.root)
                self.scan_time = time.time() - started
                with self.lock:
                    added, removed, changed = diff_trees(self.nodes, new_nodes)
                    if added or removed or changed or truncated != self.truncated:
                        self.nodes, self.truncated = new_nodes, truncated
                        self.version += 1
                        self.publish("diff", json.dumps({
                            "v": self.version, "truncated": truncated,
                            "added": added, "removed": removed, "changed": changed,
                        }, separators=(",", ":")))
            except Exception as exc:  # the loop must never die
                log("Scan error:", repr(exc))


REGISTRY = {}
REGISTRY_LOCK = threading.Lock()


def get_watcher(root):
    with REGISTRY_LOCK:
        w = REGISTRY.get(root)
        if w is None:
            w = REGISTRY[root] = Watcher(root)
        w.last_seen = time.time()
        return w


# --------------------------------------------------------------------------- #
# Web server                                                                  #
# --------------------------------------------------------------------------- #
CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".svg": "image/svg+xml",
    ".ico": "image/x-icon",
}


class Handler(BaseHTTPRequestHandler):
    server_version = f"FolderGalaxy/{__version__}"

    def log_message(self, fmt, *args):  # no log line per request
        pass

    def _send(self, code, body: bytes, ctype, extra=None):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-cache")
        self.send_header("X-Content-Type-Options", "nosniff")
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def _json(self, code, obj):
        return self._send(code, json.dumps(obj).encode(), "application/json")

    def do_GET(self):
        url = urlparse(self.path)
        path, qs = url.path, parse_qs(url.query)
        arg = lambda k: (qs.get(k) or [""])[0]

        if path == "/api/events":
            root, err = resolve_path(arg("root"))
            if err:
                return self._json(400, {"ok": False, "error": err})
            return self.events(get_watcher(root))
        if path == "/api/check":
            root, err = resolve_path(arg("root"))
            return self._json(200, {"ok": not err, "path": to_web(root) if root else None, "error": err,
                                    "base": to_web(CFG.browse_root), "default": to_web(CFG.root),
                                    "version": __version__})
        if path == "/api/dirs":
            return self.list_dirs(arg("path"))
        if path == "/api/tree":
            root, err = resolve_path(arg("root"))
            if err:
                return self._json(400, {"ok": False, "error": err})
            w = get_watcher(root)
            with w.lock:
                body = w.snapshot_payload().encode()
            return self._send(200, body, "application/json")
        if path == "/health":
            return self._send(200, b"ok", "text/plain")

        if path in ("/", "/index.html"):
            path = "/index.html"
        target = (STATIC_DIR / path.lstrip("/")).resolve()
        if STATIC_DIR not in target.parents or not target.is_file():
            return self._send(404, b"Not found", "text/plain")
        ctype = CONTENT_TYPES.get(target.suffix, "application/octet-stream")
        extra = {"Cache-Control": "public, max-age=86400"} if target.suffix == ".js" else None
        return self._send(200, target.read_bytes(), ctype, extra)

    def list_dirs(self, raw):
        """Sub-folders of a folder, used for suggestions while typing a path."""
        root, err = resolve_path(raw)
        if err:
            return self._json(200, {"ok": False, "dirs": []})
        dirs = []
        try:
            with os.scandir(root) as it:
                for e in it:
                    try:
                        if e.is_dir(follow_symlinks=False):
                            dirs.append(e.name)
                    except OSError:
                        pass
        except OSError:
            pass
        dirs.sort(key=lambda d: (d.startswith("."), d.lower()))
        return self._json(200, {"ok": True, "path": to_web(root), "dirs": dirs[:300]})

    def events(self, watcher):
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.send_header("X-Accel-Buffering", "no")
        self.end_headers()
        q = watcher.subscribe()
        try:
            self.wfile.write(b"retry: 3000\n\n")
            while True:
                try:
                    event, payload = q.get(timeout=15)
                except queue.Empty:
                    self.wfile.write(b": ping\n\n")  # keeps the connection alive
                    self.wfile.flush()
                    continue
                if event == "close":
                    break
                self.wfile.write(f"event: {event}\ndata: {payload}\n\n".encode())
                self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError, OSError):
            pass
        finally:
            watcher.unsubscribe(q)


class Server(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True


def build_config(argv=None):
    p = argparse.ArgumentParser(
        prog="folder-galaxy",
        description="Folder Galaxy - a live 3D constellation of your folders and files.",
        epilog="Every option can also be set with the environment variable shown in brackets.")
    p.add_argument("root", nargs="?", default=env("DEFAULT_ROOT", env("PROJECTS_DIR")),
                   help="folder shown when the page opens [DEFAULT_ROOT] (default: your home folder)")
    p.add_argument("--browse-root", default=env("BROWSE_ROOT"),
                   help="the page cannot leave this folder [BROWSE_ROOT] "
                        "(default: your home folder, or ROOT if it is outside it)")
    p.add_argument("--host", default=env("HOST", "127.0.0.1"),
                   help="address to listen on [HOST] (default: 127.0.0.1 = this computer only; "
                        "use 0.0.0.0 to open it from other devices)")
    p.add_argument("--port", type=int, default=int(env("PORT", "8765")), help="port [PORT] (default: 8765)")
    p.add_argument("--interval", type=float, default=float(env("SCAN_INTERVAL", "3")),
                   help="seconds between checks [SCAN_INTERVAL] (default: 3)")
    p.add_argument("--max-nodes", type=int, default=int(env("MAX_NODES", "30000")),
                   help="safety limit on the number of items [MAX_NODES] (default: 30000)")
    p.add_argument("--exclude-extra", default=env("EXCLUDE_EXTRA", ""),
                   help="extra names to ignore, comma separated, wildcards allowed [EXCLUDE_EXTRA]")
    p.add_argument("--open", action="store_true", help="open the page in the browser on start")
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    a = p.parse_args(argv)

    home = os.path.realpath(os.path.expanduser("~"))
    root = os.path.realpath(os.path.expanduser(a.root)) if a.root else home
    if a.browse_root:
        browse = os.path.realpath(os.path.expanduser(a.browse_root))
    else:
        try:
            browse = home if os.path.commonpath([root, home]) == home else root
        except ValueError:
            browse = root
    exclude = env("EXCLUDE", DEFAULT_EXCLUDE) + "," + a.exclude_extra
    return Config(root, browse, a.host, a.port, a.interval, a.max_nodes, exclude), a.open


def main(argv=None):
    global CFG
    CFG, open_browser = build_config(argv)
    _, err = resolve_path(CFG.root)
    if err:
        sys.exit(f"Error: start folder {CFG.root} is not usable ({err}). "
                 f"It must exist and be inside {CFG.browse_root}.")
    try:
        server = Server((CFG.host, CFG.port), Handler)
    except OSError as exc:
        sys.exit(f"Error: cannot listen on {CFG.host}:{CFG.port} ({exc}). Try another --port.")
    shown = "localhost" if CFG.host in ("127.0.0.1", "0.0.0.0", "::") else CFG.host
    url = f"http://{shown}:{CFG.port}"
    log(f"Folder Galaxy {__version__} - start folder {CFG.root} - browsing allowed inside {CFG.browse_root}")
    log(f"Open {url}" + ("  (also from other devices on your network)" if CFG.host == "0.0.0.0" else ""))
    if open_browser:
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        log("Bye")


if __name__ == "__main__":
    main()
