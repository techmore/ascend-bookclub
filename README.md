# Ascend Book Club — Reading Library

A static companion site for [Ascend: The Great Books Podcast](https://www.theascent.io):
every book the club has read, in reading order, with episode lists, free Q&A
guides, recommended translations and order links — plus guide pages for five
peer book clubs.

Live site: <https://techmore.github.io/ascend-bookclub/>

## Layout

| Path | What it is |
|------|------------|
| `index.html` | The library: filterable cards for every reading block, the order list, and the peer-club directory |
| `start-here.html` | Newcomer guide with three reading tracks |
| `books/*.html` | One page per reading block (episodes, guides, editions) |
| `clubs/*.html` | One page per peer club (Close Reads, Online Great Books, Cost of Glory, Pints With Jack, Word on Fire) |
| `assets/site.css` | Shared styles: colour tokens, dark mode, focus rings, skip link, nav/footer |
| `assets/tailwind.config.js` | Shared Tailwind (Play CDN) config; colours map to the CSS tokens |
| `data/archive-snapshot.json` | Snapshot of the Substack archives the site was built from |
| `scripts/check_new_posts.py` | Diffs the live Substack archives against the snapshot |
| `scripts/check_links.py` | Verifies every internal link, asset and `#fragment` resolves |

The pages are plain HTML styled with Tailwind via the Play CDN; there is no
build step. Dark mode follows the operating system (`prefers-color-scheme`).

## Run locally

```sh
python3 -m http.server 8000
# open http://localhost:8000/
```

## Checks

```sh
npx --yes html-validate@11.16.4 "**/*.html"           # HTML validity (config in .htmlvalidate.json)
python3 scripts/check_links.py . --base-prefix /ascend-bookclub   # internal links and assets
```

Both run in CI (`.github/workflows/ci.yml`) on every push and pull request.

## Keeping the library current

A scheduled workflow (`.github/workflows/watch.yml`, Mondays 12:00 UTC) runs
`scripts/check_new_posts.py --new-only` and opens an issue listing posts that
are not yet in `data/archive-snapshot.json`. The script fetches newest-first
and stops as soon as it reaches posts it already knows, falling back to the
public RSS feed if Substack's archive API refuses the request.

To file new episodes:

```sh
python3 scripts/check_new_posts.py            # report
python3 scripts/check_new_posts.py --update   # merge new posts into the snapshot
# add the episodes to the relevant books/*.html or clubs/*.html page, commit, push
```

`--full --update` re-walks the entire archive (slow; only needed to rebuild
the snapshot from scratch).

## Deploy

Pushes to `main` deploy to GitHub Pages via `.github/workflows/pages.yml`.

## Screenshots

_Add screenshots of the library index (light and dark) here._
