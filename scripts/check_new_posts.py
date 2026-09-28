#!/usr/bin/env python3
"""Check Substack archives for new posts vs committed snapshots.

Publications tracked:
  ascend     - Ascend Book Club (theascent.io)
  closereads - Close Reads Podcast HQ (closereads.substack.com)

Usage:
  python3 scripts/check_new_posts.py            # human-readable report
  python3 scripts/check_new_posts.py --update    # refresh data/archive-snapshot.json
  python3 scripts/check_new_posts.py --new-only  # print JSON of new posts (for CI)
"""
import json
import sys
import time
import urllib.error
import urllib.request

PUBS = {
    "ascend": "https://www.theascent.io",
    "closereads": "https://closereads.substack.com",
}
SNAPSHOT = "data/archive-snapshot.json"


def get_json(url):
    for attempt in range(5):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503) and attempt < 4:
                time.sleep(2 ** (attempt + 1))
                continue
            raise
    raise RuntimeError(f"gave up on {url}")


def fetch_all(base):
    posts = []
    offset = 0
    while True:
        batch = get_json(f"{base}/api/v1/archive?limit=12&offset={offset}")
        time.sleep(0.4)  # be polite to the API
        if not batch:
            break
        for p in batch:
            posts.append(
                {
                    "id": p["id"],
                    "date": (p.get("post_date") or "")[:10],
                    "title": p.get("title"),
                    "url": p.get("canonical_url"),
                }
            )
        if len(batch) < 12:
            break
        offset += 12
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


def main():
    live = {name: fetch_all(base) for name, base in PUBS.items()}
    if "--update" in sys.argv:
        with open(SNAPSHOT, "w") as f:
            json.dump(live, f, indent=1)
        for name, posts in live.items():
            print(f"snapshot updated: {name}: {len(posts)} posts")
        return
    known = load_snapshot()
    new = {}
    for name, posts in live.items():
        known_ids = {p["id"] for p in known.get(name, [])}
        fresh = [p for p in posts if p["id"] not in known_ids]
        if fresh:
            new[name] = fresh
    if "--new-only" in sys.argv:
        print(json.dumps(new))
        return
    for name, posts in live.items():
        n = len(new.get(name, []))
        print(f"{name}: live {len(posts)}, new {n}")
        for p in new.get(name, []):
            print(f"  {p['date']} | {p['title']} | {p['url']}")


if __name__ == "__main__":
    main()
