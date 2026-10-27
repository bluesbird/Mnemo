# Evaluation snapshot

This folder contains a **small, reproducible RAG sanity check** for Mnemo.
It is intended as a point-in-time quality snapshot, not a benchmark suite.

## What is included

- `fixture.json`: fixed synthetic notes + question set
- `run.py`: one isolated real-model run (no extra dependencies)
- `test_run.py`: guard tests for fixture integrity and overwrite protection
- `responses.json`: full raw run artifact
- `results.md`: human-readable summary of that run

## Current status

The committed results are a **snapshot from 27 Oct 2026**.
They are useful for transparency and reproducibility, but not a continuous or
production-quality claim.

## How to refresh

From repository root (with Docker daemon running and local Ollama models present):

```powershell
python -m unittest discover -s evaluation -p test_run.py
python .\evaluation\run.py
```

Then update `results.md` from the new `responses.json` and commit both files.
