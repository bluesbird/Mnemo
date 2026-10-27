# RAG sanity-check snapshot — 27 October 2026

> Point-in-time run artifact, not a continuous benchmark.
> See [evaluation/README.md](README.md) for scope and rerun steps.

## Run summary

- Status: **completed**
- Commit: `2f6a2903257f58ac29ed0fd66e7d630560740b66`
- Start/finish (UTC): `2026-10-27T20:12:21Z` → `2026-10-27T20:15:22Z`
- Scored questions attempted once: **10/10**
- Request failures: **0**
- Raw artifact: [responses.json](responses.json)

## Environment snapshot

- Ollama: `0.40.11`
- Embedding model: `qwen3-embedding:0.6b`
  (`ac6da0dfba84a81fdbfbaf330198c33cd77c4cdfc53e8bc50eb581914a15621d`)
- Answer model: `qwen3:4b`
  (`359d7dd4bcdab3d86b87d73ac27966f4dbb9f5efdfcc75d34a8764a09474fae7`)
- Tokenizer fallback: **false** (tokenizer loaded successfully)
- Tokenizer SHA-256 (serialized): `71241c4586582e04d5d51a420bad74d3ef5353bfdac5a53a7ba7440dbf33e350`

## Indexing snapshot

- Reconcile result: `indexed=10, skipped=0, deleted=0`
- Indexed chunks total: **16**
- Chunk distribution:
  - 7 notes with 1 chunk each
  - 3 notes with 3 chunks each

## Observations from this run

- Q8 and Q10 returned exact abstention:
  _"I don't know based on the provided notes."_
- Several answerable questions included chain-of-thought style prefaces
  ("First, I need to answer..."), and Q9 returned non-abstaining reasoning text
  despite being an absence-style question in the fixture.
- Retrieved sources often included relevant extras beyond the primary note.

This refresh intentionally reports **objective run facts** only. It does not
include manual correctness/grounding scoring.

## Reproduce

From repository root:

```powershell
python -m unittest discover -s evaluation -p test_run.py
python .\evaluation\run.py
```
