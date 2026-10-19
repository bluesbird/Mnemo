# Small RAG Sanity Check

## Scope

Phase 16: **10 fixed notes, 10 questions, one real-model run, manual review.**
No evaluation framework, LLM judge, model comparison, or statistical analysis.
Separate from deterministic CI tests.

The first run and provisional assistant-reviewed scores are recorded in
[evaluation/results.md](evaluation/results.md). Independent author review remains
outstanding. These results describe the recorded model/settings, not a separate
evaluation of the subsequently deployed Groq chat provider.

## Notes and questions

Prepare a fixed corpus with varied lengths:

- 4 short notes: a few sentences each.
- 3 medium notes: a few paragraphs each.
- 3 long notes: multiple chunks with the actual tokenizer/settings.

Use the current database notes as examples of longer writing, not as a live
dependency. Freeze selected non-sensitive text or write synthetic equivalents.
Include similar topics as distractors; not every note needs its own question.

Prepare 10 questions:

- 3 direct factual or procedural questions.
- 1 paraphrased question.
- 1 targeting a fact deep inside a long note.
- 1 combining facts from two notes.
- 1 distinguishing similar notes.
- 3 unanswerable questions: missing detail, related-but-absent fact, outside topic.

Before running, write a small **answer key**: required facts and supporting note
keys for each question, or expected abstention. No polished gold answers needed.
Accept equivalent wording.

## Run and judge

1. Load only the fixed corpus into a disposable database/index; reconcile it.
   Do not clear the normal development database.
2. Record commit, model versions and actual settings. Use current defaults,
   including `top_k=4`; confirm long notes span multiple chunks.
3. Ask each question once using the real models. Save full responses and map
   returned note IDs to fixture keys. Record errors; do not skip failed requests.
4. The project author manually judges against the answer key and full notes.
   Keep one results table with yes/no scores and short failure explanations.

## Metrics

| Metric | Pass condition | Summary |
|---|---|---|
| Correctness | All requested facts are correct and present. | _ / 7 |
| Grounding | Every factual claim is supported by the notes. | _ / 7 |
| Source coverage | All required note IDs appear in returned sources. Flag irrelevant extras separately. | _ / 7 |
| Safe abstention | Acknowledges missing evidence without inventing an answer. | _ / 3 |

Use N/A for failed requests and report their count separately; they do not count
as passes. No combined score. Returned sources are not a full retrieval trace;
do not label source coverage as retrieval recall.

## Done

Save the fixed corpus, questions/answer key, responses and short results summary.
Document failures honestly; if fixing the pipeline, retain the first run and
repeat all 10 questions. This is a sanity check, not proof of general RAG quality.
