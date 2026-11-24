"""Classify imported contacts as matches, creates, or records requiring review."""

import argparse
import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

CANONICAL = [
    {"id": "c-1", "email": "alex@example.test", "phone": "3135550101"},
    {"id": "c-2", "email": "rowan@example.test", "phone": "2485550130"},
    {"id": "c-3", "email": "maya@example.test", "phone": "7345550119"},
]
LEGACY = [
    {"id": "l-1", "email": " Alex@Example.Test ", "phone": "+1 (313) 555-0101"},
    {"id": "l-2", "email": "rowan@example.test", "phone": "7345550119"},
    {"id": "l-3", "email": "casey@example.test", "phone": "3135550199"},
    {"id": "l-4", "email": "", "phone": ""},
    {"id": "l-5", "email": "MAYA@example.test", "phone": ""},
]


def normalized(row):
    email = row.get("email", "").strip().casefold()
    phone = re.sub(r"\D", "", row.get("phone", ""))
    if len(phone) == 11 and phone.startswith("1"):
        phone = phone[1:]
    return {
        "email": email if re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email) else "",
        "phone": phone if len(phone) == 10 else "",
    }


def reconcile(source, target):
    indexes = {key: defaultdict(set) for key in ("email", "phone")}
    for row in target:
        for key, value in normalized(row).items():
            if value:
                indexes[key][value].add(row["id"])
    normalized_rows = [(row, normalized(row)) for row in source]
    frequencies = {
        key: Counter(items[key] for _, items in normalized_rows if items[key]) for key in indexes
    }
    ids = Counter(row["id"] for row in source)
    decisions = []
    for row, fields in normalized_rows:
        matches = {key: sorted(indexes[key][value]) for key, value in fields.items() if value}
        candidates = sorted({candidate for found in matches.values() for candidate in found})
        if ids[row["id"]] > 1 or any(
            value and frequencies[key][value] > 1 for key, value in fields.items()
        ):
            action, reason = "review", "duplicate identity in the source"
        elif len(candidates) > 1:
            action, reason = "review", "identity signals disagree"
        elif len(candidates) == 1:
            action, reason = "match", "one canonical identity"
        elif any(fields.values()):
            action, reason = "create", "no canonical identity matched"
        else:
            action, reason = "review", "no usable identity signal"
        decisions.append(
            {
                "source": row["id"],
                "action": action,
                "reason": reason,
                "candidates": candidates,
                "signals": matches,
            }
        )
    counts = Counter(row["action"] for row in decisions)
    return {
        "input": len(source),
        "canonical_before": len(target),
        "planned_canonical_after": len(target) + counts["create"],
        "counts": dict(counts),
        "rows": decisions,
    }


def stage_creates(source, target):
    report = reconcile(source, target)
    create_ids = {row["source"] for row in report["rows"] if row["action"] == "create"}
    created = []
    occupied = {row["id"] for row in target}
    for row in source:
        if row["id"] not in create_ids:
            continue
        fields = normalized(row)
        key = json.dumps(fields, sort_keys=True, separators=(",", ":")).encode()
        identity = "import-" + hashlib.sha256(key).hexdigest()[:24]
        if identity in occupied:
            raise ValueError("Deterministic import ID already exists with a different identity")
        occupied.add(identity)
        created.append({"id": identity, **fields})
    return report, [*target, *created]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path)
    parser.add_argument("--target", type=Path)
    parser.add_argument(
        "--stage", type=Path, help="Write only non-conflicting creates to a new local JSON snapshot"
    )
    args = parser.parse_args()
    source = json.loads(args.source.read_text(encoding="utf-8")) if args.source else LEGACY
    target = json.loads(args.target.read_text(encoding="utf-8")) if args.target else CANONICAL
    report, staged = stage_creates(source, target)
    if args.stage:
        with args.stage.open("x", encoding="utf-8") as output:
            output.write(json.dumps(staged, indent=2) + "\n")
    print(
        json.dumps(
            {
                **report,
                "staged_creates": len(staged) - len(target),
                "creates_when_repeated": reconcile(source, staged)["counts"].get("create", 0),
            },
            indent=2,
        )
    )
