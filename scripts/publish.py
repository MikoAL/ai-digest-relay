#!/usr/bin/env python3
"""Validate a daily digest JSON, render its markdown, rebuild index.json and latest.json.

Usage:
    python3 scripts/publish.py digests/YYYY-MM-DD.json   # publish one day
    python3 scripts/publish.py --check                   # validate the whole tree, write nothing

Standard library only. Exits non-zero with a message on any contract violation.
"""
from __future__ import annotations

import datetime as dt
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
DIGESTS = ROOT / "digests"
SCHEMA_VERSION = 1

KINDS = {"paper", "news", "release"}
CATEGORIES = {"architecture", "efficiency", "scaling", "training", "inference", "other"}
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")
ARXIV_RE = re.compile(r"^\d{4}\.\d{4,5}$")
HEADLINE_MAX = 140
MAX_ITEMS = 15

TOP_REQUIRED = {"schema_version", "date", "generated_at", "items"}
TOP_OPTIONAL = {"notes"}
ITEM_REQUIRED = {"id", "kind", "title", "url", "source", "category", "on_focus",
                 "headline", "summary", "critique"}
ITEM_OPTIONAL = {"result", "authors", "arxiv_id"}


class Invalid(Exception):
    pass


def _str(obj: dict, key: str, where: str, max_len: int | None = None) -> str:
    v = obj.get(key)
    if not isinstance(v, str) or not v.strip():
        raise Invalid(f"{where}.{key}: must be a non-empty string")
    if max_len is not None and len(v) > max_len:
        raise Invalid(f"{where}.{key}: {len(v)} chars exceeds limit {max_len}")
    return v


def _keys(obj: dict, required: set, optional: set, where: str) -> None:
    missing = required - obj.keys()
    unknown = obj.keys() - required - optional
    if missing:
        raise Invalid(f"{where}: missing keys {sorted(missing)}")
    if unknown:
        raise Invalid(f"{where}: unknown keys {sorted(unknown)}")


def validate(d: object, expected_date: str | None = None) -> dict:
    if not isinstance(d, dict):
        raise Invalid("digest: top level must be an object")
    _keys(d, TOP_REQUIRED, TOP_OPTIONAL, "digest")
    if d["schema_version"] != SCHEMA_VERSION:
        raise Invalid(f"digest.schema_version: expected {SCHEMA_VERSION}")

    date = _str(d, "date", "digest")
    if not DATE_RE.match(date):
        raise Invalid("digest.date: must be YYYY-MM-DD")
    dt.date.fromisoformat(date)
    if expected_date is not None and date != expected_date:
        raise Invalid(f"digest.date {date} does not match file name {expected_date}")

    ts = dt.datetime.fromisoformat(_str(d, "generated_at", "digest"))
    if ts.tzinfo is None:
        raise Invalid("digest.generated_at: must include a UTC offset")

    if "notes" in d:
        _str(d, "notes", "digest")

    items = d["items"]
    if not isinstance(items, list) or not 1 <= len(items) <= MAX_ITEMS:
        raise Invalid(f"digest.items: must be a list of 1..{MAX_ITEMS} items")

    ids, urls = set(), set()
    for i, it in enumerate(items):
        w = f"items[{i}]"
        if not isinstance(it, dict):
            raise Invalid(f"{w}: must be an object")
        _keys(it, ITEM_REQUIRED, ITEM_OPTIONAL, w)

        iid = _str(it, "id", w)
        if not ID_RE.match(iid):
            raise Invalid(f"{w}.id: must match {ID_RE.pattern}")
        if iid in ids:
            raise Invalid(f"{w}.id: duplicate '{iid}'")
        ids.add(iid)

        if it["kind"] not in KINDS:
            raise Invalid(f"{w}.kind: must be one of {sorted(KINDS)}")
        if it["category"] not in CATEGORIES:
            raise Invalid(f"{w}.category: must be one of {sorted(CATEGORIES)}")
        if not isinstance(it["on_focus"], bool):
            raise Invalid(f"{w}.on_focus: must be a boolean")

        url = _str(it, "url", w)
        if not url.startswith("https://"):
            raise Invalid(f"{w}.url: must start with https://")
        if url in urls:
            raise Invalid(f"{w}.url: duplicate '{url}'")
        urls.add(url)

        for key in ("title", "source", "summary", "critique"):
            _str(it, key, w)
        _str(it, "headline", w, HEADLINE_MAX)

        if it["kind"] == "paper":
            _str(it, "result", w)
        elif "result" in it:
            _str(it, "result", w)
        if "authors" in it:
            a = it["authors"]
            if not isinstance(a, list) or not a or not all(isinstance(x, str) and x.strip() for x in a):
                raise Invalid(f"{w}.authors: must be a non-empty list of strings")
        if "arxiv_id" in it:
            if not isinstance(it["arxiv_id"], str) or not ARXIV_RE.match(it["arxiv_id"]):
                raise Invalid(f"{w}.arxiv_id: must match {ARXIV_RE.pattern}")
    return d


def render_md(d: dict) -> str:
    items = d["items"]
    out = [f"# AI Digest — {d['date']}", "",
           f"_Generated {d['generated_at']} · {len(items)} items · focus: architectures & efficiency_", ""]
    if "notes" in d:
        out += [f"> {d['notes']}", ""]

    def block(n: int, it: dict) -> list[str]:
        meta = [it["source"], it["kind"], it["category"]]
        if "arxiv_id" in it:
            meta.append(f"arXiv:{it['arxiv_id']}")
        lines = [f"### {n}. [{it['title']}]({it['url']})", "", " · ".join(meta)]
        if "authors" in it:
            authors = it["authors"]
            shown = ", ".join(authors[:6]) + (" et al." if len(authors) > 6 else "")
            lines.append(f"_{shown}_")
        lines += ["", f"**In one line:** {it['headline']}", "", f"**What:** {it['summary']}", ""]
        if "result" in it:
            lines += [f"**Result:** {it['result']}", ""]
        lines += [f"**Critique:** {it['critique']}", ""]
        return lines

    n = 0
    for title, flag in (("On focus", True), ("Also notable", False)):
        group = [it for it in items if it["on_focus"] is flag]
        if not group:
            continue
        out += [f"## {title}", ""]
        for it in group:
            n += 1
            out += block(n, it)
    return "\n".join(out).rstrip() + "\n"


def dumps(obj: object) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=2) + "\n"


def digest_files() -> list[pathlib.Path]:
    return sorted((p for p in DIGESTS.glob("*.json") if DATE_RE.match(p.stem)),
                  key=lambda p: p.stem, reverse=True)


def load(p: pathlib.Path) -> dict:
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise Invalid(f"{p.name}: invalid JSON ({e})") from e
    try:
        return validate(data, p.stem)
    except Invalid as e:
        raise Invalid(f"{p.name}: {e}") from e


def build_index(digests: list[dict]) -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "updated_at": digests[0]["generated_at"] if digests else None,
        "digests": [{
            "date": d["date"],
            "item_count": len(d["items"]),
            "on_focus_count": sum(it["on_focus"] for it in d["items"]),
            "top_headline": d["items"][0]["headline"],
            "json": f"digests/{d['date']}.json",
            "md": f"digests/{d['date']}.md",
        } for d in digests],
    }


def check() -> list[str]:
    errors: list[str] = []
    digests = []
    for p in digest_files():
        try:
            d = load(p)
        except Invalid as e:
            errors.append(str(e))
            continue
        digests.append(d)
        md = p.with_suffix(".md")
        if not md.exists():
            errors.append(f"{md.name}: missing")
        elif md.read_text(encoding="utf-8") != render_md(d):
            errors.append(f"{md.name}: out of date with {p.name}")
    if errors:
        return errors

    idx = DIGESTS / "index.json"
    if not idx.exists() or idx.read_text(encoding="utf-8") != dumps(build_index(digests)):
        errors.append("index.json: missing or out of date")
    latest = DIGESTS / "latest.json"
    if digests:
        if not latest.exists() or json.loads(latest.read_text(encoding="utf-8")) != digests[0]:
            errors.append("latest.json: missing or not identical to the newest digest")
    elif latest.exists():
        errors.append("latest.json: present but there are no digests")
    return errors


def publish(path: pathlib.Path) -> None:
    path = path.resolve()
    if path.parent != DIGESTS or not DATE_RE.match(path.stem) or path.suffix != ".json":
        raise Invalid(f"{path}: must be digests/YYYY-MM-DD.json")
    d = load(path)
    path.write_text(dumps(d), encoding="utf-8")  # normalize formatting
    path.with_suffix(".md").write_text(render_md(d), encoding="utf-8")

    digests = [load(p) for p in digest_files()]
    (DIGESTS / "index.json").write_text(dumps(build_index(digests)), encoding="utf-8")
    (DIGESTS / "latest.json").write_text(dumps(digests[0]), encoding="utf-8")


def main(argv: list[str]) -> int:
    try:
        if argv == ["--check"]:
            pass
        elif len(argv) == 1:
            publish(pathlib.Path(argv[0]))
        else:
            print(__doc__, file=sys.stderr)
            return 2
    except (Invalid, ValueError) as e:
        print(f"INVALID: {e}", file=sys.stderr)
        return 1
    errors = check()
    for e in errors:
        print(f"INVALID: {e}", file=sys.stderr)
    if errors:
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
