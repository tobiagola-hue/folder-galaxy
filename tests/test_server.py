"""Tests for Folder Galaxy. Run with:  python -m unittest discover -s tests -v"""
import json
import os
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import server  # noqa: E402


def make_tree(base):
    """base/
         proj/a.py (10 B)  proj/sub/b.txt (5 B)  proj/.git/x  proj/node_modules/y
         other/c.md (3 B)
    """
    def w(rel, data):
        path = os.path.join(base, *rel.split("/"))
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            f.write(data)
    w("proj/a.py", "x" * 10)
    w("proj/sub/b.txt", "y" * 5)
    w("proj/.git/x", "ignored")
    w("proj/node_modules/y", "ignored")
    w("other/c.md", "z" * 3)


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = os.path.realpath(self.tmp.name)
        make_tree(self.base)
        self.outside = tempfile.TemporaryDirectory()
        server.CFG, _ = server.build_config([os.path.join(self.base, "proj"), "--browse-root", self.base])

    def tearDown(self):
        self.tmp.cleanup()
        self.outside.cleanup()


class ResolvePathTests(Base):
    def test_inside_is_allowed(self):
        path, err = server.resolve_path(os.path.join(self.base, "other"))
        self.assertIsNone(err)
        self.assertEqual(path, os.path.join(self.base, "other"))

    def test_empty_means_start_folder(self):
        path, err = server.resolve_path("")
        self.assertEqual(path, os.path.join(self.base, "proj"))

    def test_outside_is_refused(self):
        self.assertEqual(server.resolve_path(self.outside.name)[1], "outside")

    def test_dot_dot_cannot_escape(self):
        self.assertEqual(server.resolve_path(os.path.join(self.base, "proj", "..", ".."))[1], "outside")

    def test_missing_folder(self):
        self.assertEqual(server.resolve_path(os.path.join(self.base, "nope"))[1], "missing")

    def test_relative_paths_are_relative_to_browse_root(self):
        self.assertEqual(server.resolve_path("other")[0], os.path.join(self.base, "other"))

    @unittest.skipIf(os.name == "nt", "symlinks need extra rights on Windows")
    def test_symlink_pointing_outside_is_refused(self):
        link = os.path.join(self.base, "escape")
        os.symlink(self.outside.name, link)
        self.assertEqual(server.resolve_path(link)[1], "outside")


class ScanTests(Base):
    def test_sizes_counts_and_excludes(self):
        nodes, truncated = server.scan_tree(self.base)
        self.assertFalse(truncated)
        self.assertNotIn("proj/.git", nodes)
        self.assertNotIn("proj/node_modules", nodes)
        self.assertEqual(nodes["proj"]["f"], 2)
        self.assertEqual(nodes["proj"]["s"], 15)
        self.assertEqual(nodes[""]["f"], 3)
        self.assertEqual(nodes[""]["s"], 18)
        self.assertEqual(nodes["proj/sub/b.txt"]["p"], "proj/sub")

    @unittest.skipIf(os.name == "nt", "symlinks need extra rights on Windows")
    def test_symlinked_folders_are_not_followed(self):
        os.symlink(self.outside.name, os.path.join(self.base, "link"))
        with open(os.path.join(self.outside.name, "secret.txt"), "w") as f:
            f.write("s")
        nodes, _ = server.scan_tree(self.base)
        self.assertEqual(nodes["link"]["t"], "f")  # shown as a plain entry, never entered
        self.assertFalse(any("secret" in k for k in nodes))

    def test_max_nodes(self):
        server.CFG.max_nodes = 3
        nodes, truncated = server.scan_tree(self.base)
        self.assertTrue(truncated)
        self.assertLessEqual(len(nodes), 3)

    def test_extra_excludes_with_wildcards(self):
        server.CFG, _ = server.build_config([self.base, "--browse-root", self.base, "--exclude-extra", "*.md,sub"])
        nodes, _ = server.scan_tree(self.base)
        self.assertNotIn("other/c.md", nodes)
        self.assertNotIn("proj/sub", nodes)
        self.assertIn("proj/a.py", nodes)


class DiffTests(unittest.TestCase):
    def test_added_removed_changed(self):
        old = {"": {"id": "", "s": 1, "m": 1, "f": 1}, "a": {"id": "a", "s": 1, "m": 1}}
        new = {"": {"id": "", "s": 2, "m": 2, "f": 1}, "b": {"id": "b", "s": 1, "m": 2}}
        added, removed, changed = server.diff_trees(old, new)
        self.assertEqual([n["id"] for n in added], ["b"])
        self.assertEqual(removed, ["a"])
        self.assertEqual([n["id"] for n in changed], [""])

    def test_parents_are_added_first(self):
        new = {"x/y/z": {"id": "x/y/z"}, "x": {"id": "x"}, "x/y": {"id": "x/y"}}
        added, _, _ = server.diff_trees({}, new)
        self.assertEqual([n["id"] for n in added], ["x", "x/y", "x/y/z"])


class HttpTests(Base):
    def setUp(self):
        super().setUp()
        self.httpd = server.Server(("127.0.0.1", 0), server.Handler)
        self.port = self.httpd.server_address[1]
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()

    def tearDown(self):
        self.httpd.shutdown()
        self.httpd.server_close()
        super().tearDown()

    def get(self, path):
        return urllib.request.urlopen(f"http://127.0.0.1:{self.port}{path}", timeout=5)

    def test_page_is_served(self):
        body = self.get("/").read().decode()
        self.assertIn("Folder Galaxy", body)

    def test_static_traversal_is_blocked(self):
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self.get("/../server.py")
        self.assertEqual(ctx.exception.code, 404)

    def test_check_endpoint(self):
        data = json.load(self.get("/api/check?root=" + urllib.request.quote(self.outside.name)))
        self.assertFalse(data["ok"])
        self.assertEqual(data["error"], "outside")
        data = json.load(self.get("/api/check?root="))
        self.assertTrue(data["ok"])

    def test_dirs_endpoint(self):
        data = json.load(self.get("/api/dirs?path=" + urllib.request.quote(self.base)))
        self.assertEqual(data["dirs"], ["other", "proj"])

    def test_events_start_with_a_snapshot(self):
        resp = self.get("/api/events?root=" + urllib.request.quote(self.base))
        lines = []
        while len(lines) < 3:
            line = resp.readline().decode().strip()
            if line:
                lines.append(line)
        self.assertEqual(lines[1], "event: snapshot")
        snap = json.loads(lines[2][len("data: "):])
        self.assertEqual(snap["nodes"][0]["id"], "")
        resp.close()

    def test_events_outside_are_refused(self):
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self.get("/api/events?root=" + urllib.request.quote(self.outside.name))
        self.assertEqual(ctx.exception.code, 400)


if __name__ == "__main__":
    unittest.main()
