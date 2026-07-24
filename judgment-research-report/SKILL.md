---
name: judgment-research-report
description: Create Word-table case retrieval reports from Word or PDF judgments and case materials. Use when Codex needs to draft a 案例检索报告, 类案检索表, 案例摘录表, or judgment research report from .docx/.doc/.pdf inputs, especially when each case must include 序号, 案件名称, 案号, 基本案情, and user-specified extraction factors guided by a stated research purpose.
---

# Judgment Research Report

## Overview

Use this skill to turn Word or PDF judgment materials into a case retrieval report, normally as a Word table. The core job is to preserve the case accurately while tailoring the emphasis to the user stated research purpose.

## Start Every Task

Before drafting, confirm these items from the user if they are not already provided:

1. The research purpose: what issue the report is meant to prove, compare, evaluate, or support.
2. The extra extraction factors: one or more columns beyond the fixed columns.
3. The input scope: which Word/PDF files, folder, or selected cases to include.
4. The desired output filename. If absent, choose a clear Chinese filename based on the research purpose.

If the user provides a reference sample, first summarize the extraction rules inferred from that sample and ask the user to confirm before applying them.

## Default Table

Create a Word table by default. The required fixed columns are:

1. 序号
2. 案件名称
3. 案号
4. 基本案情
5. User-specified extra extraction factor columns

Only add other fixed columns when the user asks or the input sample clearly requires them.

## Fixed Column Rules

- 序号: assign report-local numbers from 1 in the final sorting order. Do not copy numbering from source documents.
- 案件名称: extract the full judgment title, preserving parties, cause of action, trial level, and document type. Do not shorten it into a casual case name.
- 案号: extract the formal case number exactly, preserving parentheses, year, court abbreviation, case type, and serial number.
- 基本案情: write one compact paragraph that restores the case facts first. Include the key dispute conduct, lawsuit or claim, court determination, and final result. Lightly use the research purpose to adjust emphasis, but do not let it override faithful case reconstruction.

For 基本案情, vary the emphasis by research purpose:

- Entity or conduct research: add 1-3 sentences on the accused conduct, transaction background, technical feature, contractual performance, public statement, or other factual detail that matters to the issue.
- Damages or liability research: emphasize loss, bad faith, scale, duration, causation, responsibility allocation, remedies, and whether the appellate court changed the result.
- Procedural or evidence research: include procedural posture, burden of proof, key evidence, preservation, appraisal, notarization, or court treatment of evidence when important.

## Extra Extraction Factors

Extra columns should be more strongly guided by the research purpose than 基本案情. Extract and organize only the content that helps answer the purpose.

Common extra factors include:

- 裁判观点 or 法院认定: summarize the holding or reasoning relevant to the purpose.
- 酌定因素: extract the factors the court used to determine damages or responsibility.
- 判赔金额: state the amount and whether it includes reasonable expenses.
- 被诉行为: summarize the conduct, channel, statements, duration, audience, and scale.
- 证据与证明: identify key evidence and how the court accepted or rejected it.
- 责任承担: state who bears liability, joint liability, injunctions, apologies, statements, or other remedies.

When a source has direct court language that is especially important, quote briefly and accurately. Otherwise summarize in polished report language.

For every user-specified extra extraction factor column, preserve the relevant source reasoning more fully than a normal summary. This rule applies only to extra extraction columns, not to the fixed columns 序号, 案件名称, 案号, or 基本案情. For extra columns that ask for court reasoning, objections, defenses, 抗辩回应, 主体适格性, 裁判观点, 酌定因素, or similar analysis, do not extract only the conclusion. Capture the reasoning chain: the party's challenge or defense, the legal rule or standard, the court's factual application, and the final conclusion. Prefer direct judgment wording with quotation marks, using short connector phrases only where needed. If the relevant reasoning is long, set a rough cell-length budget and use ellipses to skip unrelated passages; if the judgment contains little relevant reasoning, do not pad with weakly related text.

For extra columns focused on a specific legal issue, loosely follow this writing order when the source permits: first identify the party's objection, claim, or defense; then quote the court's governing rule or review standard; then quote or summarize the court's application of that rule to the key facts; finally state the court's conclusion. Use short lead-ins such as "某方抗辩", "法院认为", and "据此认定" to make the logic easy to scan. If the judgment gives only a conclusion or a case-summary excerpt, say so instead of inventing missing reasoning.

## Source Handling

- Word files: use DOCX/document tools to extract tables and paragraphs. Preserve tracked-change awareness if the source contains revisions.
- PDF files: first extract text with a PDF text tool. If extraction is empty, garbled, or only page markers, treat the PDF as scanned. Render representative pages to confirm readability, then run OCR before drafting. If local OCR is unavailable or fails, look for a reliable duplicate text source such as an official/public PDF copy, court/public account page, database text, or the same file at a public URL; cite or note that fallback source in the final response. If no reliable OCR/text source can be obtained, mark the affected row or field as extraction-limited rather than guessing.
- Multiple files: treat each judgment as one candidate row unless the user asks to merge related proceedings.
- Missing fields: mark uncertain or absent information clearly, such as 未检索到 or 原文未载明, rather than inventing it.

## Writing Style

- Write in Chinese legal research style: concise, accurate, and useful for comparison.
- Prefer faithful synthesis over full-text copying.
- Keep 基本案情 readable as a paragraph; use numbered points in extra columns when multiple factors must be distinguished.
- Avoid overfitting to the research purpose: the table should still let a reader understand what happened in the case.
- If source documents conflict, state the conflict and use the judgment text as the primary source unless the user directs otherwise.

## Output

Deliver a .docx report unless the user asks for another format. Use a clear table layout, repeat header row when possible, and keep long text cells legible with paragraph breaks or numbered items.

## Word Table Formatting

When creating the default Word report table, match the established case-retrieval sample style unless the user provides a different sample or asks for another format:

- Use `楷体_GB2312` for all table text. Use 小四 size, approximately 12 pt, unless the user provides a different reference sample for that task.
- Use automatic numbering for the `序号` column rather than manually typed digits, so deleting or reordering rows can update numbering with normal Word/WPS list behavior.
- Format the first row as the table header: apply the sample-style light gray fill `E0E0E0`, bold all header text, and center header text vertically and horizontally.
- Do not fill body rows by default. Keep body text regular weight.
- Center compact identifier columns such as 序号 and 案号; left-align longer narrative columns such as 案件名称, 基本案情, and extra extraction factors.
- Vertically center all table cells by default. Keep horizontal alignment rules unchanged: compact identifier columns may stay horizontally centered, while longer narrative columns remain horizontally left-aligned.
- Keep the header row repeated across pages when the table spans multiple pages.
- If the user supplies a reference report, inspect and follow that report's table style first; otherwise use the defaults above.
