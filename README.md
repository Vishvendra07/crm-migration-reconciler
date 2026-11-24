# CRM Migration Reconciler

Normalize two sets of contact records and surface disagreement when email and phone point to different candidates.

[Source](project.py) · [Demo evidence](evidence/demo.json) · [Verification](evidence/checks.json)

## Run locally

Requires Python 3.11+.

```sh
python project.py
python -m unittest discover -v
```

## Engineering decision

Treat conflicting signals and duplicate source IDs as review cases. Produce planned counts and record reasons before any merge action can occur.

Authored sandbox records and US phone normalization. No actual CRM writes.



[Technology or project reference](https://docs.python.org/3/library/collections.html)
