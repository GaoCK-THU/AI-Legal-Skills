# Contract Redline Skill

Generate native Microsoft Word tracked changes from structured contract-review intentions. The language model is responsible for the legal judgment and complete proposed clause; deterministic Python tooling anchors the clause, preflights the edit, renders Word revision markup, and verifies the result.

## What is included

- `SKILL.md`: the end-to-end review and delivery workflow.
- `scripts/contract_pipeline.py`: snapshots a DOCX, validates high-level intents, and creates a safe application plan.
- `scripts/word_redline.py`: applies and verifies tracked changes and comments in DOCX XML.
- `tests/`: regression tests for the pipeline and Word-redline engine.
- `references/`: review framework, schemas, and failure-handling rules.

## Requirements

- Python 3.10+
- A native `.docx` file
- `pytest` for the regression suite

The core scripts use the Python standard library. Install the test dependency with:

```bash
python3 -m pip install -r requirements-dev.txt
python3 -m pytest -q
```

## Safe usage model

1. Make a snapshot of the current contract.
2. Prepare structured high-level review intentions using stable paragraph anchors.
3. Let the pipeline preflight the changes in a temporary copy.
4. Apply only the generated plan.
5. Verify revision counts, author, timestamp, and XML integrity.

Read `SKILL.md` before use. It explains why a contract-review conclusion must not be converted directly into low-level string replacements: the program validates where and how the final Word change is written.

## Privacy and legal note

No contract, client information, test output, or generated redline is included. This tool supports document execution; it does not replace legal review, transaction context, or the user's final approval.

## Status

Prepared for open-source release; run the regression suite before publishing.
