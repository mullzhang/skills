---
name: collect-review-docs
description: Collect review-reference documents from a user-specified local folder, mounted Google Drive folder, or shared drive mirror without reading document contents. Use when the user asks Codex to inspect only file names, paths, timestamps, or metadata; group candidate specs/design/infra/requirements documents; ask the user which documents and destination to use; then copy selected files while converting Google Workspace shortcuts (.gdoc, .gsheet, .gslides) to AI-readable Office formats.
---

# Collect Review Docs

## Overview

Use this skill to build a safe review-document pack from a folder or mounted shared drive. The workflow has two hard boundaries: do not inspect document bodies during discovery, and never modify or delete source files.

## Workflow

1. Confirm the source scope. Use the folder or mounted Drive path supplied by the user. If the source is a Google Drive URL rather than a local mounted path, use available Drive tools only for metadata and export; do not fetch document text.
2. List candidates from metadata only. Run `scripts/list_doc_candidates.py <source-folder>` or equivalent `find`/`stat` commands. Use only filenames, relative paths, extensions, sizes, and modified times.
3. Present grouped candidates:
   - Priority high: likely system-review entry points such as API design, ER diagrams, UI/screen specs, feature lists, screen transitions, infrastructure diagrams, infrastructure settings, security specs, and environment build logs.
   - Requirements/specification context: procurement specs, question lists, client answers, update requests, received/sent requirement files, customization notes.
   - Operations/nonfunctional context: infrastructure, AWS, security, account lists, load tests, environment setup, operations notes.
   - History/decision context: meeting notes, MTG materials, hearing notes, WBS, project structure, service overview, handoff notes.
   - Scope/commercial context: contracts, estimates, delivery, acceptance, invoices. Note that these are usually lower priority for technical review unless scope confirmation matters.
4. Ask for the user's selection and destination. Do not copy anything until the user identifies the documents or group(s) to copy and the destination directory.
5. Copy safely. Use `scripts/copy_selected_docs.py <source-folder> <destination-folder> --paths-file <selection-file>` when practical. Preserve relative directories by default. Refuse overwrites unless the user explicitly approves `--overwrite`.
6. Convert Workspace shortcuts. Convert local `.gdoc` to `.docx`, `.md`, and `.txt`; `.gsheet` to `.xlsx`; and `.gslides` to `.pptx` using Google Drive export (`gws drive files export` or an available Google Drive export tool). Reading the local shortcut JSON only to obtain the file ID is allowed; reading the actual document contents is not.
7. Verify by metadata only. After copying, list destination filenames, sizes, and optionally modified times. Do not open or summarize copied document contents unless the user gives a separate explicit instruction.

## Safety Rules

- Do not read the body of PDFs, Office files, Markdown files, Draw.io files, Google Docs, Google Sheets, Google Slides, images, recordings, SQL dumps, or text documents during discovery.
- Do not use text extraction, previews, screenshots, thumbnail reads, document fetches, or grep over document contents.
- Do not modify, rename, move, or delete source files.
- Treat `.gdoc`, `.gsheet`, and `.gslides` files as metadata pointers. Read only the shortcut JSON fields needed for export, typically `doc_id`, `resource_key`, and account metadata.
- Keep all user-facing candidate lists grounded in metadata. Phrases such as "likely" or "appears to be" are appropriate because classification is inferred from names and paths.
- If a conversion requires network or Drive credentials and fails due authorization, sandboxing, or network access, request approval or ask the user to provide an accessible export path; do not fall back to reading the local document body.

## Scripts

### `scripts/list_doc_candidates.py`

Use this to produce grouped candidates without reading document bodies.

```bash
python /path/to/collect-review-docs/scripts/list_doc_candidates.py "/path/to/source"
```

Useful options:

- `--json` for machine-readable output.
- `--max-per-group N` to keep the displayed candidate list concise.
- `--include-all` to include low-signal document-like files that the default filters omit.

### `scripts/copy_selected_docs.py`

Use this after the user selects files. Create a newline-delimited paths file containing relative paths from the source root. Lines beginning with `#` are ignored.

```bash
python /path/to/collect-review-docs/scripts/copy_selected_docs.py "/path/to/source" "/path/to/destination" --paths-file /tmp/selection.txt
```

Useful options:

- `--dry-run` to show planned outputs without writing.
- `--overwrite` only after explicit user approval.
- `--flat` only if the user asks not to preserve source subdirectories.
- `--gws-binary <command>` if the Drive CLI is not named `gws`.

## Conversion Defaults

Use these export formats unless the user requests another AI-readable format:

| Source | Output |
|---|---|
| `.gdoc` | `.docx`, `.md`, `.txt` |
| `.gsheet` | `.xlsx` |
| `.gslides` | `.pptx` |

For non-Workspace files, copy the original format unchanged. Do not convert `.pdf`, `.drawio`, `.md`, Office files, images, or CSVs unless the user explicitly asks. The `.md` and `.txt` sidecars for Google Docs are deliberate: many AI readers handle them more reliably than `.docx`, especially when the source document contains many images or complex layout.

## Reporting

When reporting candidates, state that the list is based only on filenames and timestamps. When reporting completion, include the destination directory, the count of copied/exported files, and any files skipped or failed.
