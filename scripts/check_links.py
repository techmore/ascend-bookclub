#!/usr/bin/env python3
"""Check that every internal link and asset reference in the site resolves.

Walks all *.html files under the site root, resolves relative and root-
relative hrefs/srcs against the file system, and verifies #fragments point
at an existing id. External (http/https) URLs are not fetched. Also flags
http:// assets that would be blocked as mixed content on an https site.

Usage: python3 scripts/check_links.py [site-root] [--base-prefix /repo-name]
Exit status 1 when a broken reference is found.
"""
import os
import sys
from html.parser import HTMLParser
from urllib.parse import unquote, urlparse

SKIP_DIRS = {".git", "node_modules", "_site", "venv", ".venv", "__pycache__"}
URL_ATTRS = ("href", "src", "poster", "data-src")


class Refs(HTMLParser):
    def __init__(self):
        super().__init__()
        self.refs = []  # (tag, attr, url, line)
        self.ids = set()

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        line = self.getpos()[0]
        if a.get("id"):
            self.ids.add(a["id"])
        if a.get("name") and tag == "a":
            self.ids.add(a["name"])
        for attr in URL_ATTRS:
            if a.get(attr):
                self.refs.append((tag, attr, a[attr], line))
        if a.get("srcset"):
            for part in a["srcset"].split(","):
                url = part.strip().split(" ")[0]
                if url:
                    self.refs.append((tag, "srcset", url, line))


def main():
    args = [x for x in sys.argv[1:] if not x.startswith("--")]
    root = os.path.abspath(args[0] if args else ".")
    prefix = ""
    if "--base-prefix" in sys.argv:
        prefix = sys.argv[sys.argv.index("--base-prefix") + 1].rstrip("/")

    pages = {}
    for d, dirs, files in os.walk(root):
        dirs[:] = sorted(x for x in dirs if x not in SKIP_DIRS and not x.startswith("."))
        for f in sorted(files):
            if f.endswith((".html", ".htm")):
                path = os.path.join(d, f)
                p = Refs()
                p.feed(open(path, encoding="utf-8", errors="replace").read())
                pages[path] = p

    problems = []
    for path, p in pages.items():
        rel = os.path.relpath(path, root)
        for tag, attr, url, line in p.refs:
            u = url.strip()
            if not u or u.startswith(("mailto:", "tel:", "javascript:", "data:")):
                continue
            if u.startswith("#"):
                if u[1:] and u[1:] not in p.ids:
                    problems.append(f"{rel}:{line}: missing fragment {u}")
                continue
            pr = urlparse(u)
            if pr.scheme in ("http", "https") or u.startswith("//"):
                if u.startswith("http://") and (attr != "href" or tag in ("link", "script", "iframe")):
                    problems.append(f"{rel}:{line}: mixed content (http://) {u}")
                continue
            if pr.scheme:
                continue
            fpath = unquote(pr.path)
            if fpath.startswith("/"):
                if prefix and (fpath == prefix or fpath.startswith(prefix + "/")):
                    fpath = fpath[len(prefix):] or "/"
                target = os.path.join(root, fpath.lstrip("/"))
            elif fpath:
                target = os.path.normpath(os.path.join(os.path.dirname(path), fpath))
            else:
                target = path
            if os.path.isdir(target):
                target = os.path.join(target, "index.html")
            if not os.path.exists(target):
                problems.append(f"{rel}:{line}: broken <{tag} {attr}=\"{u}\">")
            elif pr.fragment and target in pages and pr.fragment not in pages[target].ids:
                problems.append(f"{rel}:{line}: missing fragment #{pr.fragment} in {u}")

    print(f"checked {len(pages)} pages, {sum(len(p.refs) for p in pages.values())} references")
    for msg in problems:
        print("  " + msg)
    if problems:
        print(f"FAIL: {len(problems)} problem(s)")
        sys.exit(1)
    print("OK: no broken internal links or assets")


if __name__ == "__main__":
    main()
