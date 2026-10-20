#!/usr/bin/env python3
"""Check Substack archives for new posts vs committed snapshots.

Publications tracked:
  ascend     - Ascend Book Club (theascent.io)
  closereads - Close Reads Podcast HQ (closereads.substack.com)

Usage:
  python3 scripts/check_new_posts.py            # human-readable report
  python3 scripts/check_new_posts.py --update    # merge new posts into data/archive-snapshot.json
  python3 scripts/check_new_posts.py --new-only  # print JSON of new posts (for CI)
  python3 scripts/check_new_posts.py --full      # page through the whole archive (slow; use with --update to rebuild)

How it fetches
  1. Substack's archive API, newest first, stopping as soon as a page contains
     only posts we already know (so a weekly check is 1-2 requests per site,
     not ~100, which kept tripping Substack's rate limit / 403 bot wall).
  2. If the API is blocked (403/429 after retries), fall back to the public
     RSS feed, which carries the latest ~20 posts.  Posts found via RSS are
     matched by canonical URL.
  3. A publication that cannot be reached at all is reported on stderr and
     the script exits 2 after printing what it could find.
"""
import json
import sys
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime

PUBS = {
    "ascend": "https://www.theascent.io",
    "closereads": "https://closereads.substack.com",
}
SNAPSHOT = "data/archive-snapshot.json"
PAGE = 12
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/129.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
}


class Blocked(Exception):
    """The remote refused us (403/429) even after retries."""


def fetch(url, accept=None):
    headers = dict(HEADERS)
    if accept:
        headers["Accept"] = accept
    last = None
    for attempt in range(4):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            last = e
            if e.code in (403, 429, 500, 502, 503) and attempt < 3:
                time.sleep(2 ** (attempt + 1))
                continue
            if e.code in (403, 429):
                raise Blocked(f"{url} -> HTTP {e.code}") from e
            raise
        except (urllib.error.URLError, TimeoutError) as e:
            last = e
            if attempt < 3:
                time.sleep(2 ** (attempt + 1))
                continue
            raise
    raise RuntimeError(f"gave up on {url}: {last}")


def get_json(url):
    return json.loads(fetch(url).decode())


def normalise(p):
    return {
        "id": p["id"],
        "date": (p.get("post_date") or "")[:10],
        "title": p.get("title"),
        "url": p.get("canonical_url"),
    }


def fetch_api(base, known_ids, full=False):
    """Newest-first pages; stop when a whole page is already known (unless full)."""
    posts = []
    offset = 0
    while True:
        batch = get_json(f"{base}/api/v1/archive?limit={PAGE}&offset={offset}")
        if not batch:
            break
        page = [normalise(p) for p in batch]
        posts.extend(page)
        if not full and all(p["id"] in known_ids for p in page):
            break
        if len(batch) < PAGE:
            break
        offset += PAGE
        time.sleep(0.6)  # be polite to the API
    return posts


def fetch_rss(base):
    """Latest ~20 posts from the public feed. ids are unknown; url is the key."""
    xml = fetch(f"{base}/feed", accept="application/rss+xml, application/xml, text/xml, */*")
    root = ET.fromstring(xml)
    posts = []
    for item in root.iter("item"):
        link = (item.findtext("link") or item.findtext("guid") or "").strip()
        title = (item.findtext("title") or "").strip()
        date = ""
        pub = item.findtext("pubDate")
        if pub:
            try:
                date = parsedate_to_datetime(pub).strftime("%Y-%m-%d")
            except (TypeError, ValueError):
                pass
        posts.append({"id": None, "date": date, "title": title, "url": link})
    return posts


def load_snapshot():
    try:
        with open(SNAPSHOT) as f:
            data = json.load(f)
    except FileNotFoundError:
        return {}
    # migrate legacy flat-list format (ascend only)
    if isinstance(data, list):
        return {"ascend": data}
    return data


def find_new(name, base, known, full=False):
    """Return (new_posts, source) for one publication; raises on total failure."""
    known_ids = {p["id"] for p in known if p.get("id") is not None}
    known_urls = {p["url"] for p in known if p.get("url")}
    try:
        live = fetch_api(base, known_ids, full=full)
        source = "api"
    except Blocked as e:
        print(f"warning: {name}: archive API blocked ({e}); falling back to RSS", file=sys.stderr)
        live = fetch_rss(base)
        source = "rss"
    fresh = [p for p in live if (p["id"] is None or p["id"] not in known_ids) and p["url"] not in known_urls]
    return fresh, source, live


def main():
    full = "--full" in sys.argv
    known = load_snapshot()
    new = {}
    sources = {}
    live_all = {}
    failures = []
    for name, base in PUBS.items():
        try:
            fresh, source, live = find_new(name, base, known.get(name, []), full=full)
        except Exception as e:  # noqa: BLE001 - report and keep going with the other publication
            print(f"error: {name}: could not fetch archive: {e}", file=sys.stderr)
            failures.append(name)
            continue
        sources[name] = source
        live_all[name] = live
        if fresh:
            new[name] = fresh

    if "--update" in sys.argv:
        merged = dict(known)
        for name, fresh in new.items():
            merged[name] = fresh + known.get(name, [])
        if full:
            for name, live in live_all.items():
                if sources[name] == "api":
                    merged[name] = live
        with open(SNAPSHOT, "w") as f:
            json.dump(merged, f, indent=1)
            f.write("\n")
        for name in PUBS:
            print(f"snapshot updated: {name}: {len(merged.get(name, []))} posts (+{len(new.get(name, []))} new)")
    elif "--new-only" in sys.argv:
        print(json.dumps(new))
    else:
        for name in PUBS:
            if name in failures:
                print(f"{name}: FAILED")
                continue
            print(f"{name}: known {len(known.get(name, []))}, new {len(new.get(name, []))} (via {sources[name]})")
            for p in new.get(name, []):
                print(f"  {p['date']} | {p['title']} | {p['url']}")

    if failures:
        sys.exit(2)


if __name__ == "__main__":
    main()
