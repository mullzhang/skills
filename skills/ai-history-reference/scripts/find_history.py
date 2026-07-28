#!/usr/bin/env python3
"""Find locally archived ChatGPT and SpecStory Markdown conversations."""

from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path
from typing import Any


UUID_RE = re.compile(
    r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b",
    re.IGNORECASE,
)


def first_match(pattern: str, text: str) -> str | None:
    match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
    return match.group(1).strip() if match else None


def extract_metadata(path: Path, source: str, text: str) -> dict[str, Any]:
    title = first_match(r"^#\s+(.+?)\s*$", text) or path.stem
    link = first_match(r"^\*\*Link:\*\*\s+\[[^\]]+\]\((https?://[^)]+)\)", text)
    link = link or first_match(r"^\*\*Link:\*\*\s+(https?://\S+)", text)
    conversation_id = None
    if link:
        conversation_id = first_match(r"/c/([0-9a-f-]{36})(?:[/?#]|$)", link)

    session_id = first_match(
        r"^(?:session_id|session-id|sessionId):\s*[\"']?([^\"'\s]+)", text
    )
    if not session_id and source == "specstory":
        filename_ids = UUID_RE.findall(path.name)
        session_id = filename_ids[-1] if filename_ids else None

    return {
        "path": str(path.resolve()),
        "source": "ChatGPT Chat" if source == "chatgpt" else "SpecStory",
        "title": title,
        "conversation_id": conversation_id,
        "session_id": session_id,
        "link": link,
        "created": first_match(r"^\*\*Created:\*\*\s+(.+?)\s*$", text),
        "updated": first_match(r"^\*\*Updated:\*\*\s+(.+?)\s*$", text),
        "exported": first_match(r"^\*\*Exported:\*\*\s+(.+?)\s*$", text),
        "modified_epoch": path.stat().st_mtime,
    }


def rank_candidate(
    path: Path,
    metadata: dict[str, Any],
    text: str,
    query: str | None,
    requested_id: str | None,
) -> tuple[int, list[str]]:
    folded_text = text.casefold()
    folded_title = str(metadata["title"]).casefold()
    folded_stem = path.stem.casefold()
    reasons: list[str] = []
    score = 0

    if requested_id:
        folded_id = requested_id.casefold()
        identifiers = {
            str(metadata.get("conversation_id") or "").casefold(),
            str(metadata.get("session_id") or "").casefold(),
        }
        if folded_id in identifiers:
            score = 10_000
            reasons.append("exact ID")
        elif folded_id in folded_text or folded_id in folded_stem:
            score = 9_000
            reasons.append("ID in file")
        else:
            return 0, []

    if query:
        folded_query = query.casefold().strip()
        if not folded_query:
            return score, reasons

        if folded_title == folded_query:
            score += 2_000
            reasons.append("exact title")
        elif folded_stem == folded_query:
            score += 1_800
            reasons.append("exact filename")
        elif folded_query in folded_title:
            score += 1_500
            reasons.append("title contains query")
        elif folded_query in folded_stem:
            score += 1_300
            reasons.append("filename contains query")
        elif folded_query in folded_text:
            score += 1_000
            reasons.append("body contains query")
        else:
            tokens = [token for token in re.split(r"\s+", folded_query) if token]
            searchable = f"{folded_title}\n{folded_stem}\n{folded_text}"
            if tokens and all(token in searchable for token in tokens):
                score += 700
                reasons.append("all query terms")

    return score, reasons


def selected_roots(source: str, archive_roots: dict[str, Path]) -> dict[str, Path]:
    if source == "all":
        return archive_roots
    return {source: archive_roots[source]}


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Search central ChatGPT and SpecStory Markdown archives."
    )
    parser.add_argument("query", nargs="?", help="Title, topic, project, or text query")
    parser.add_argument("--id", dest="requested_id", help="Conversation or session ID")
    parser.add_argument(
        "--source",
        choices=("all", "chatgpt", "specstory"),
        default="all",
        help="Limit the archive source",
    )
    default_history_root = Path(
        os.environ.get("AI_HISTORY_ROOT", str(Path.home() / "ai-history"))
    ).expanduser()
    parser.add_argument(
        "--history-root",
        type=Path,
        default=default_history_root,
        help="Archive root (default: AI_HISTORY_ROOT or ~/ai-history)",
    )
    parser.add_argument("--limit", type=int, default=10, help="Maximum candidates")
    args = parser.parse_args()

    if not args.query and not args.requested_id:
        parser.error("provide a query or --id")
    if args.limit < 1:
        parser.error("--limit must be at least 1")

    missing_roots: list[str] = []
    candidates: list[dict[str, Any]] = []
    history_root = args.history_root.expanduser()
    archive_roots = {
        "chatgpt": history_root / "chatgpt-chat",
        "specstory": history_root / "specstory",
    }
    roots = selected_roots(args.source, archive_roots)

    for source, root in roots.items():
        if not root.is_dir():
            missing_roots.append(str(root))
            continue

        for path in root.rglob("*.md"):
            if not path.is_file():
                continue
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
                metadata = extract_metadata(path, source, text)
                score, reasons = rank_candidate(
                    path, metadata, text, args.query, args.requested_id
                )
            except OSError:
                continue

            if score:
                metadata["score"] = score
                metadata["match_reason"] = reasons
                candidates.append(metadata)

    candidates.sort(
        key=lambda item: (item["score"], item["modified_epoch"]), reverse=True
    )
    for candidate in candidates:
        candidate.pop("modified_epoch", None)

    result = {
        "query": args.query,
        "requested_id": args.requested_id,
        "source": args.source,
        "archive_roots": {key: str(value) for key, value in roots.items()},
        "missing_roots": missing_roots,
        "candidate_count": len(candidates),
        "candidates": candidates[: args.limit],
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
