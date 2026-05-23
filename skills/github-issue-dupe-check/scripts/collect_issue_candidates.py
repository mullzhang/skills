#!/usr/bin/env python3
"""Collect likely duplicate GitHub issues with gh.

The script intentionally stops at candidate collection. Duplicate judgment is
left to the agent because it depends on user-visible symptoms and likely fixes.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Any


STOPWORDS = {
    "and",
    "about",
    "after",
    "again",
    "also",
    "because",
    "before",
    "being",
    "below",
    "between",
    "cannot",
    "could",
    "directory",
    "does",
    "doing",
    "entries",
    "from",
    "have",
    "not",
    "into",
    "issue",
    "like",
    "more",
    "only",
    "suggestions",
    "should",
    "that",
    "the",
    "their",
    "there",
    "these",
    "this",
    "those",
    "through",
    "using",
    "when",
    "where",
    "with",
    "would",
}

GENERIC_CODE_TERMS = {
    "github/ISSUE_TEMPLATE/3-cli.yml",
    "openai/codex",
}


def run_json(cmd: list[str]) -> Any:
    result = subprocess.run(cmd, text=True, capture_output=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(
            f"command failed ({result.returncode}): {' '.join(cmd)}\n{result.stderr.strip()}"
        )
    if not result.stdout.strip():
        return None
    return json.loads(result.stdout)


def run_text(cmd: list[str]) -> str:
    result = subprocess.run(cmd, text=True, capture_output=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(
            f"command failed ({result.returncode}): {' '.join(cmd)}\n{result.stderr.strip()}"
        )
    return result.stdout.strip()


def infer_repo() -> str:
    return run_text(["gh", "repo", "view", "--json", "nameWithOwner", "-q", ".nameWithOwner"])


def read_draft(path: Path) -> tuple[str, str]:
    body = path.read_text(encoding="utf-8")
    title = ""
    for line in body.splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            title = stripped[2:].strip()
            break
    if not title:
        for line in body.splitlines():
            stripped = line.strip()
            if stripped:
                title = re.sub(r"^#+\s*", "", stripped)
                break
    return title, body


def words(text: str) -> list[str]:
    text = text.replace("$", " dollar sign ")
    return [
        token.lower()
        for token in re.findall(r"[A-Za-z][A-Za-z0-9_$./:-]{2,}", text)
        if token.lower() not in STOPWORDS
    ]


def code_terms(text: str) -> list[str]:
    terms: list[str] = []
    terms.extend(re.findall(r"`([^`\n]{3,80})`", text))
    terms.extend(re.findall(r"\b[A-Za-z0-9_.-]+/[A-Za-z0-9_./-]{2,}\b", text))
    terms.extend(re.findall(r"\b[A-Z][A-Z0-9_]{3,}\b", text))
    cleaned: list[str] = []
    seen: set[str] = set()
    for term in terms:
        term = term.strip().strip(".,;:")
        if not term or term in seen or term in GENERIC_CODE_TERMS:
            continue
        if "/" in term and not any(marker in term for marker in (".", "_", "~", "cache", "codex")):
            continue
        seen.add(term)
        cleaned.append(term)
    return cleaned


def symptom_queries(title: str, body: str) -> list[str]:
    text = f"{title}\n{body}".lower()
    queries: list[str] = []

    if "$" in text or "dollar sign" in text:
        if "autocomplete" in text or "menu" in text:
            queries.append("dollar sign menu autocomplete")
        if "app" in text:
            queries.append("dollar sign menu app suggestions")
            queries.append("Dollar sign menu bloated")
            queries.append("dollar sign menu bloated irrelevant")

    if "autocomplete" in text and "app" in text:
        queries.append("autocomplete app suggestions")

    if "inaccessible" in text or "isaccessible" in text:
        queries.append("inaccessible app autocomplete")

    return queries


def make_queries(title: str, body: str, extra_queries: list[str], max_queries: int) -> list[str]:
    queries: list[str] = []

    if title:
        queries.append(title)

    queries.extend(symptom_queries(title, body))

    term_counts = Counter(words(f"{title}\n{body}"))
    top_terms = [term for term, _count in term_counts.most_common(10)]
    if top_terms:
        queries.append(" ".join(top_terms[:8]))
        queries.append(" ".join(top_terms[:5]))

    terms = code_terms(body)
    if terms:
        queries.append(" ".join(terms[:6]))
        for term in terms[:4]:
            queries.append(term)

    queries.extend(extra_queries)

    deduped: list[str] = []
    seen: set[str] = set()
    for query in queries:
        query = re.sub(r"\s+", " ", query).strip()
        if len(query) > 220:
            query = query[:220].rsplit(" ", 1)[0]
        key = query.lower()
        if not query or key in seen:
            continue
        seen.add(key)
        deduped.append(query)
    return deduped[:max_queries]


def search_issues(repo: str, query: str, limit: int, state: str) -> list[dict[str, Any]]:
    cmd = [
        "gh",
        "issue",
        "list",
        "--repo",
        repo,
        "--search",
        query,
        "--limit",
        str(limit),
        "--json",
        "number,title,state,url,updatedAt,labels,comments",
    ]
    cmd.extend(["--state", state])
    data = run_json(cmd)
    return data or []


def issue_details(repo: str, number: int) -> dict[str, Any]:
    return run_json(
        [
            "gh",
            "issue",
            "view",
            str(number),
            "--repo",
            repo,
            "--json",
            "number,title,state,url,body,comments,labels,createdAt,updatedAt",
        ]
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Collect likely duplicate GitHub issues with gh.")
    parser.add_argument("--repo", help="Repository in owner/name form. Defaults to gh repo view.")
    parser.add_argument("--draft", type=Path, help="Markdown issue draft. First H1 is used as title.")
    parser.add_argument("--title", help="Issue title when --draft is not used.")
    parser.add_argument("--body", default="", help="Issue body text when --draft is not used.")
    parser.add_argument("--query", action="append", default=[], help="Extra search query. Repeatable.")
    parser.add_argument("--state", choices=["all", "open", "closed"], default="all")
    parser.add_argument("--limit-per-query", type=int, default=10)
    parser.add_argument("--max-queries", type=int, default=8)
    parser.add_argument("--max-issues", type=int, default=20)
    parser.add_argument("--output", type=Path, help="Write JSON report to this path.")
    args = parser.parse_args()

    repo = args.repo or infer_repo()
    if args.draft:
        title, body = read_draft(args.draft)
    else:
        title = args.title or ""
        body = args.body or ""

    if not title and not body and not args.query:
        parser.error("provide --draft, --title/--body, or at least one --query")

    queries = make_queries(title, body, args.query, args.max_queries)
    candidates: dict[int, dict[str, Any]] = {}
    order: list[int] = []

    for query in queries:
        try:
            results = search_issues(repo, query, args.limit_per_query, args.state)
        except RuntimeError as exc:
            print(str(exc), file=sys.stderr)
            continue
        for item in results:
            number = int(item["number"])
            if number not in candidates:
                item["matchedQueries"] = []
                candidates[number] = item
                order.append(number)
            candidates[number]["matchedQueries"].append(query)

    detailed: list[dict[str, Any]] = []
    for number in order[: args.max_issues]:
        item = candidates[number]
        try:
            detail = issue_details(repo, number)
            detail["matchedQueries"] = item["matchedQueries"]
            detailed.append(detail)
        except RuntimeError as exc:
            item["detailError"] = str(exc)
            detailed.append(item)

    report = {
        "repo": repo,
        "title": title,
        "queries": queries,
        "candidateCount": len(candidates),
        "candidates": detailed,
    }

    output = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        args.output.write_text(output + "\n", encoding="utf-8")
    else:
        print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
