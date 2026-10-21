# Small RAG sanity check — 17 October 2026

## Run

One scored run, **10 questions asked once**, following one unscored chat warmup.
All 10 requests returned HTTP 200; **0 request errors**. No pipeline tuning or
retries of scored questions.

- Code: `81478af11ac3a127f24927094efdc233e6f6eb4c`, dirty working tree.
  The exact dirty paths, fixture SHA-256, timestamps, model metadata, effective
  settings, indexed chunk texts, note hashes and full API responses are saved in
  [responses.json](responses.json). Production RAG code was unchanged.
- Ollama `0.40.5`; embedding `qwen3-embedding:0.6b`, Q8_0,
  digest `ac6da0dfba84a81fdbfbaf330198c33cd77c4cdfc53e8bc50eb581914a15621d`;
  answering `qwen3:4b`, Q4_K_M,
  digest `359d7dd4bcdab3d86b87d73ac27966f4dbb9f5efdfcc75d34a8764a09474fae7`.
  Digests unchanged afterwards; no model downloads.
- Defaults: retrieval `top_k=4`, minimum dense score `0.4`, chat context `4096`,
  temperature `0.1`, `think=false`; no seed specified. Other model defaults are
  recorded via `/api/show`. The existing client strips text before `</think>`;
  the warmup did emit such text despite `think=false`.
- Actual tokenizer: `Qwen/Qwen3-Embedding-0.6B` at
  `97b0c614be4d77ee51c0cef4e5f07c00f9eb65b3`; **no fallback**.
  It loaded in the indexing service logs and again in the inspection process.
  Configured chunk size/overlap: `400/50` (the existing overlap uses words).
- Original synthetic corpus: **4 short, 3 medium, 3 long notes; 16 indexed chunks**.
  Short notes have 67–74 tokens and medium notes 187–202 tokens.
  All three long notes produced **3 actual indexed chunks each**, 150–369 tokens
  per chunk. Q5's receipt fact is in archive paragraph 6, indexed chunk 1
  (zero-based), not the opening chunk.

Note ID → fixture key (also recorded with hashes and counts in the raw JSON):
`1 willow-access`, `2 willow-loans`, `3 harbor-loans`, `4 seed-library`,
`5 printer-recovery`, `6 archive-release`, `7 willow-packing`,
`8 archive-handbook`, `9 garden-handbook`, `10 festival-handbook`.
IDs 1–7 each have one chunk; IDs 8–10 each have three.

## Manual judgments

**Reviewed by the coding assistant, not by the project author. These scores are
provisional until the author accepts the review.** I checked every answerable
response against its frozen required facts and the complete fixture notes,
including additional assertions. No LLM judge or automatic answer scoring.

Correctness requires every key fact; grounding requires support for every factual
claim; coverage requires all specified note IDs in returned sources. Unrelated
extras do not fail coverage. “Extra” below means an extra returned source, not a
claim made in the answer. Chunk numbers are zero-based.

| Case | Correct | Grounded | Source coverage | Safe abstention | Evidence / issue; extra sources |
|---|---|---|---|---|---|
| Q1 direct | Yes | Yes | Yes | N/A | Tuesday/Thursday, 18:00–20:00 all present, supported by `willow-access`. Unrelated extras: `harbor-loans`, `festival-handbook:0`, `willow-loans`. |
| Q2 procedure | Yes | Yes | Yes | N/A | All five steps, roll orientation, order and three-second hold match `printer-recovery`; no unsupported additions. Unrelated extras: `archive-handbook:2,1`, `archive-release`. |
| Q3 release gate | Yes | Yes | Yes | N/A | Redact all visible address labels; second volunteer checks page order against intake sheet, both supported by `archive-release`. Extra `archive-handbook:1` gives related background; its chunks 0 and 2 do not supply the requested checks. |
| Q4 paraphrase | Yes | Yes | Yes | N/A | Two packets maximum per visit; no immediate replacement required, both supported by `seed-library`. Unrelated extras: `garden-handbook:1,2`, `archive-handbook:2`. |
| Q5 deep fact | Yes | Yes | Yes | N/A | 45 days after public release, then locked shredding bin, exactly supported by `archive-handbook:1`. Extras `archive-release` and `festival-handbook:2` do not answer retention; returned archive chunk 2 adds no requested fact. |
| Q6 two notes | Yes | Yes | Yes | N/A | Thursday 18:30–19:00 and all three pouch items present. Extra assertion “at the green desk” is supported by `willow-loans`; items by `willow-packing`. Unrelated extras: `harbor-loans`, `willow-access`. |
| Q7 similar notes | **No** | Yes | Yes | N/A | Correctly rejects Willow's Saturday window and gives Thursday 18:30–19:00. Strict frozen-key failure: does not explicitly attribute Saturday 10:00–11:00 to Harbor. Both required notes returned. Unrelated extras: `willow-access`, `willow-packing`. |
| Q8 missing detail | N/A | N/A | N/A | Yes | Exact “I don't know based on the provided notes.” No telephone number invented; no sources. |
| Q9 related absence | N/A | N/A | N/A | Yes | Same exact abstention; no lunar recommendation invented; no sources. |
| Q10 outside topic | N/A | N/A | N/A | Yes | Same exact abstention; no Jupiter percentage invented; no sources. |

**Correctness: 6/7. Grounding: 7/7. Source coverage: 7/7.
Safe abstention: 3/3. Failed requests: 0.** No combined score.
Q7 is a conservative completeness judgment, not a wrong Willow schedule:
the question already supplies Harbor's hours, but the frozen key explicitly
requires their attribution. That fact was not restated; the key was not relaxed
after seeing the response.

## Isolation, limitations and reproduction

The runner reused the existing E2E Compose topology and built current Knowledge service/RAG service
images. Only a unique project/network, fresh PostgreSQL and fresh Chroma were
used; no host ports, development mounts or personal notes. Events were disabled
in RAG service so the explicit reconcile deterministically indexed all ten notes
(`indexed=10, skipped=0, deleted=0`). This does not evaluate event ingestion.
The host Ollama was the only shared runtime.

An initial **setup-only** attempt failed on RabbitMQ cookie permissions before
loading notes or asking questions. Its failure and successful cleanup are
preserved in `responses.json` under `setup_attempts`. An evaluation-only cookie
permission override resolved it; no RAG settings changed. Both projects'
containers, volumes and networks were removed. Development containers remained
running. Generated startup/service diagnostics remain ignored in `.run`.

This is a tiny English synthetic sanity check, not general quality evidence.
Only one long note is directly questioned; returned sources contain unrelated
extras on all seven answerable cases. Source coverage is **not retrieval recall**
or proof of precise citations. No model comparison, statistics or deterministic
generation claim.

From the repository root, with Docker and the two local Ollama models available:

```powershell
python -m unittest discover -s evaluation -p test_run.py
python .\evaluation\run.py
```

The three focused standard-library tests passed. The runner refuses to overwrite
`responses.json`; preserve this run elsewhere before intentionally starting any
future run, and ask all ten questions again rather than retrying failures.
It writes partial results immediately and always attempts isolated teardown,
even if diagnostic collection fails. No extra dependencies or CI changes.
