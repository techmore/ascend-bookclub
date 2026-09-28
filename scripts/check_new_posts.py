#!/usr/bin/env python3
"""Check the Ascend Substack archive for new posts vs the committed snapshot.

Usage:
  python3 scripts/check_new_posts.py            # human-readable report
  python3 scripts/check_new_posts.py --update    # refresh data/archive-snapshot.json
  python3 scripts/check_new_posts.py --new-only  # print JSON of posts not in snapshot (for CI)
"""
import json
import sys
import urllib.request

ARCHIVE_URL = "https://www.theascent.io/api/v1/archive?limit=12&offset={}"
SNAPSHOT = "data/archive-snapshot.json"


def fetch_all():
    posts = []
    offset = 0
    while True:
        req = urllib.request.Request(
            ARCHIVE_URL.format(offset), headers={"User-Agent": "Mozilla/5.0"}
        )
        with urllib.request.urlopen(req, timeout=30) as r:
            batch = json.loads(r.read().decode())
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
            return json.load(f)
    except FileNotFoundError:
        return []


def main():
    live = fetch_all()
    if "--update" in sys.argv:
        with open(SNAPSHOT, "w") as f:
            json.dump(live, f, indent=1)
        print(f"snapshot updated: {len(live)} posts")
        return
    known = {p["id"] for p in load_snapshot()}
    new = [p for p in live if p["id"] not in known]
    if "--new-only" in sys.argv:
        print(json.dumps(new))
        return
    print(f"live posts: {len(live)}, snapshot: {len(known)}, new: {len(new)}")
    for p in new:
        print(f"  {p['date']} | {p['title']} | {p['url']}")


if __name__ == "__main__":
    main()
