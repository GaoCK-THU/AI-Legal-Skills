---
name: smart-evidence-shots
description: Extract stable, representative screenshots from videos by interpreting the user's instructions and, when provided, example screenshots. Use when Codex is asked to 截图, 智能截图, 取证截图, extract key frames, find visually or contextually specified moments in a video, or use example images as templates for locating corresponding video content. Optionally package approved screenshots into a time-labeled PDF when the user requests it.
---

# Smart Evidence Shots

## Core Objective

Infer what content the user wants from their instructions and example screenshots, locate matching intervals in the video, and extract the clearest stable representative frames. Keep target-content identification separate from stable-frame selection: first decide whether an interval contains the requested content, then choose the best frame within that interval.

## Workflow

1. Read the user's written instructions and inspect every example screenshot. For each target screenshot category, infer:
   - what content or relationship must be visible;
   - which visual details may vary without changing the target meaning;
   - what would make a visually similar frame irrelevant.
2. Resolve material ambiguity before the full scan. Ask the minimum necessary clarification questions when unresolved ambiguities would materially change which screenshots are selected. Keep each question specific and combine related uncertainties when practical. Continue without confirmation when the target is sufficiently clear.
3. Inspect the full relevant video range with a method suited to its length and complexity. Use temporal samples, contact sheets, timeline thumbnails, scene-change cues, or direct review as appropriate. Treat overviews as useful global navigation aids, not as the only valid inspection method, and do not assume that fixed-interval samples alone will reveal brief targets.
4. Locate candidate intervals through visual and contextual understanding. Compare objects, people, text, layout, interface state, actions, and relationships according to the user's intended meaning rather than requiring a pixel-level match. Inspect enough surrounding context to distinguish a true match from a coincidental visual resemblance. Increase temporal sampling density around plausible matches, transitions, or brief appearances.
5. Treat each detected time as a candidate interval, not a final screenshot. Inspect nearby frames at a sufficiently fine temporal resolution, including sub-second frames when needed. Select a frame only when it both represents the requested content and is stable, clear, complete, and minimally obstructed.
6. Extract every final screenshot from the original video at its original resolution.
7. Check the final set against every inferred target category and the requested coverage. Remove near-duplicates only when they represent the same target occurrence and add no useful visual or contextual information. Preserve additional frames when they show materially different content or provide reasonable alternatives under uncertainty; mark alternatives clearly in the manifest.
8. Deliver the final screenshots as the primary review artifact. Also generate `evidence_manifest.csv`, `evidence_manifest.md`, and overview sheets to support completeness checks, error review, timecode traceability, and optional PDF generation. At minimum, map each screenshot to a unique ID, timecode, source seconds, target category, filename, description, and review note.
9. Generate a PDF only when the user requests it or approves the screenshots. Do not create a PDF by default immediately after screenshot extraction.

## Screenshot Selection Rules

- Treat target relevance and stability as separate requirements. A stable frame is not useful unless it matches the user's target, and a matching frame is not deliverable unless it is stable.
- Reject or replace frames with meaningful motion, transition, loading, blur, incomplete content, or unintended obstruction. Do not use a player, recording, export, or application-switching interface as the final screenshot unless the user explicitly targets it.
- Prefer one best stable representative for the same target occurrence. Add another screenshot only when it contributes distinct requested information or is a useful alternative that cannot be resolved confidently.
- When two stable frames are both plausible and the difference may matter to the user's intent, retain both as clearly marked alternatives instead of making an irreversible choice without sufficient basis.
- Report a missing stable match honestly when the target appears only in unusable frames; do not substitute an unrelated or unstable frame merely to complete the output set.

## PDF Rules

Create the PDF only after screenshot review or an explicit request. Put exactly one full-bleed screenshot on each page and preserve the screenshot's page size.

Follow any time-label style explicitly requested by the user. Otherwise use this default:

- white rectangle fill;
- black 1pt border;
- black Helvetica text;
- 28pt font;
- top-left position with 18pt margin;
- text containing only the time, such as `00:58`.

## Reference

Read `references/workflow.md` when you need detailed guidance for interpreting examples, choosing a video inspection strategy, judging stability, handling alternatives, or building manifests and review artifacts.

## Scripts

- Use `scripts/video_frames.swift` for deterministic video metadata, review-frame sampling, overview generation, and precise original-resolution extraction. Use its outputs to support visual judgment; do not treat the script as a target-content classifier.
- Use `scripts/create_time_pdf.py` only after the user requests a PDF or approves the screenshots. It reads `evidence_manifest.csv` by default and accepts an optional JSON label-style configuration.
- Read `references/workflow.md` for command patterns, intermediate manifest roles, and the supported PDF style keys.
