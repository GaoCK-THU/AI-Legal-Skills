# Judgment Research Report Skill

Turn a human-selected set of judgments or case materials into a consistent, purpose-driven Word case-research report. The workflow preserves core case facts while tailoring additional columns—such as reasoning, damages, evidence, or liability—to the stated research question.

## What is included

- `SKILL.md`: instructions for extracting fields, handling PDF and Word sources, and formatting the final Word table.

## Intended workflow

1. The researcher defines the legal question and selects candidate cases.
2. The agent reads the selected materials and extracts fixed fields: sequence number, case name, docket number, and basic facts.
3. The agent adds only the issue-specific fields that answer the research question.
4. A human reviewer checks comparability, quotations, and the final Word report.

This split is deliberate: search results and case comparability remain a lawyer's decision; the Skill focuses on reading, structured extraction, and uniform reporting.

## Privacy and source note

This package includes no judgments, database exports, client case materials, or generated reports. When using commercial legal databases, comply with their access terms and do not redistribute source text unless authorized.

## Status

Prepared as a prompt-and-workflow Skill. A future release may add generic document-processing helpers only after they are separated from case-specific scripts and test materials.
