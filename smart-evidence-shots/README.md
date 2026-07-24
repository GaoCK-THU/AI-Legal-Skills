# Smart Evidence Shots

Extract clear, stable, evidence-relevant screenshots from a video. The workflow separates two judgments: whether a moment contains the requested evidence, and which nearby frame is the clearest stable representative. It can create a time-labelled PDF only after the screenshots are approved.

## What is included

- `SKILL.md`: the reusable agent workflow.
- `scripts/video_frames.swift`: deterministic video sampling, contact-sheet generation, and full-resolution extraction.
- `scripts/create_time_pdf.py`: one approved screenshot per PDF page with a time label.
- `references/workflow.md`: operational detail and command patterns.

## Requirements

- macOS with Swift (for `video_frames.swift` and AVFoundation)
- Python 3.10+ with `reportlab` and `Pillow` (for PDF output)
- An MP4 or other AVFoundation-readable source video

Install Python dependencies:

```bash
python3 -m pip install -r requirements.txt
```

## Quick start

Read `SKILL.md`, sample the source video with `scripts/video_frames.swift`, review the candidate moments, then extract approved original-resolution frames. Run `scripts/create_time_pdf.py` only after human approval. The precise commands and manifest format are documented in `references/workflow.md`.

## Privacy and evidence note

This repository intentionally ships no real recordings or screenshots. Do not upload source videos, manifests, or PDFs that contain personal information, account details, or client materials without a separate authorization and review process.

## Status

Prepared for open-source release; validate the toolchain on a clean local video before publishing.
