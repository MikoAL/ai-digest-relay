# ai-digest-relay

A daily AI research digest (focus: model architectures and training/inference efficiency), published as data.

- **Writer:** a scheduled Claude run at 09:20 Asia/Taipei. It is the only thing that writes to `digests/`.
- **Readers:** a Discord bot (polls `latest.json` over HTTP) and a static website (to be built in this repo).

No secrets live in this repo, and there are no GitHub Actions involved in delivery.

## Layout

```
digests/
  index.json          manifest of all digests, newest first (generated)
  latest.json         byte-for-byte content of the newest digest (generated)
  YYYY-MM-DD.json     one digest; the only file the run writes by hand
  YYYY-MM-DD.md       human-readable rendering of the JSON (generated)
scripts/
  publish.py          validator + renderer; stdlib only
```

`YYYY-MM-DD` is the Taipei-local date of the run.

## Publishing (writer)

```sh
python3 scripts/publish.py digests/2026-10-17.json   # validate, render .md, rebuild index.json + latest.json
python3 scripts/publish.py --check                   # validate the whole tree, write nothing
```

Both exit non-zero with an `INVALID:` message on any contract violation. Nothing is pushed unless `--check` prints `OK`.

## Data contract — schema_version 1

`publish.py` is the source of truth; this table describes it. Unknown keys are rejected.

### Digest (`YYYY-MM-DD.json`, `latest.json`)

| Field | Type | Notes |
|---|---|---|
| `schema_version` | int | `1` |
| `date` | string | `YYYY-MM-DD`, Taipei date; matches the file name |
| `generated_at` | string | ISO 8601 with UTC offset |
| `notes` | string, optional | e.g. "No new arXiv batch today (weekend)." |
| `items` | array | 1–15 items, in display order |

### Item

| Field | Type | Notes |
|---|---|---|
| `id` | string | slug `[a-z0-9-]`, ≤64 chars, unique within the digest |
| `kind` | string | `paper` \| `news` \| `release` |
| `title` | string | |
| `url` | string | `https://`, unique within the digest |
| `source` | string | e.g. `arXiv`, `HF Daily Papers`, `Google DeepMind blog` |
| `category` | string | `architecture` \| `efficiency` \| `scaling` \| `training` \| `inference` \| `other` |
| `on_focus` | bool | `true` if within architectures/efficiency |
| `headline` | string | ≤140 chars; the line the Discord bot posts |
| `summary` | string | problem and method |
| `result` | string | required for `paper`, optional otherwise; key quantitative result vs. baselines |
| `critique` | string | limitations, weak baselines, missing ablations, unverified claims |
| `authors` | string[], optional | |
| `arxiv_id` | string, optional | e.g. `2610.01234` |

### Index (`index.json`)

```json
{
  "schema_version": 1,
  "updated_at": "2026-10-17T09:41:00+08:00",
  "digests": [
    {"date": "2026-10-17", "item_count": 10, "on_focus_count": 8,
     "top_headline": "…", "json": "digests/2026-10-17.json", "md": "digests/2026-10-17.md"}
  ]
}
```

`updated_at` is `null` and `digests` is empty until the first digest exists. A static site cannot list a directory, so it should discover dates through this file.

## Discord bot (reader)

- Fetch `https://raw.githubusercontent.com/MikoAL/ai-digest-relay/main/digests/latest.json`.
- `404` means no digest has been published yet.
- Post only if `date` equals today's Taipei date and that date has not been posted before (store the last posted date).
- raw.githubusercontent.com caches for about 5 minutes. The run usually finishes 15–40 minutes after 09:20, so poll from about 10:00 and retry every 15 minutes until about 12:00. If nothing new by then, the run failed or was skipped.
- Message: one line per item from `headline` (≤140 chars each), plus a link to the day's page. Discord's limit is 2,000 characters per message, so split if needed.

## Website (reader)

`index.html` at the repo root, served by GitHub Pages from `main` at <https://mikoal.github.io/ai-digest-relay/>. One file, no dependencies, no build step. It reads `digests/index.json` and the per-day JSON files and never modifies anything under `digests/` or `scripts/`, so a new digest shows up on the next page load.

- `#YYYY-MM-DD` selects a day; no hash shows the newest one.
- Read/favorite marks and the theme live in the viewer's localStorage.
- `.nojekyll` makes Pages serve files as-is.
- Spec: `docs/superpowers/specs/2026-10-19-website-design.md`.

Preview locally (fetch does not work from `file://`):

```sh
python3 -m http.server   # then open http://localhost:8000/
```
