#!/usr/bin/env python3
"""List review-document candidates using filenames and filesystem metadata only."""

from __future__ import annotations

import argparse
import json
import os
import stat as stat_module
import unicodedata
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable


DOCUMENT_EXTS = {
    ".csv",
    ".doc",
    ".docx",
    ".drawio",
    ".gdoc",
    ".gsheet",
    ".gslides",
    ".md",
    ".odp",
    ".ods",
    ".odt",
    ".pdf",
    ".ppt",
    ".pptx",
    ".rtf",
    ".tsv",
    ".txt",
    ".xls",
    ".xlsx",
}

LOW_SIGNAL_EXTS = {
    ".heic",
    ".jpeg",
    ".jpg",
    ".json",
    ".m4a",
    ".mp4",
    ".png",
    ".py",
    ".sh",
    ".sql",
    ".svg",
}

GROUPS = [
    (
        "priority_high",
        "Priority high",
        [
            "api設計",
            "api_design",
            "api design",
            "api対応",
            "web-api",
            "er図",
            "er diagram",
            "画面仕様",
            "ui画面仕様",
            "機能一覧",
            "画面遷移",
            "aws構成図",
            "インフラ設定書",
            "インフラストラクチャ",
            "セキュリティ仕様",
            "環境構築log",
            "環境構築ログ",
        ],
    ),
    (
        "requirements",
        "Requirements/specification context",
        [
            "仕様書",
            "要件",
            "要求",
            "機能一覧",
            "質問",
            "回答",
            "受領",
            "送付",
            "アップデート",
            "update",
            "改修",
            "カスタマイズ",
            "確認事項",
            "フォーマット",
            "ラフ仕様",
            "入力項目",
        ],
    ),
    (
        "operations_nonfunctional",
        "Operations/nonfunctional context",
        [
            "インフラ",
            "aws",
            "セキュリティ",
            "負荷テスト",
            "performance",
            "アカウント",
            "設定",
            "環境構築",
            "運用",
            "本番環境",
            "pre",
            "main",
        ],
    ),
    (
        "history_decisions",
        "History/decision context",
        [
            "議事",
            "議事録",
            "議事メモ",
            "mtg",
            "打ち合わせ",
            "打合せ",
            "ヒアリング",
            "定例",
            "wbs",
            "体制",
            "全体像",
            "サービス全体像",
            "引き続き",
            "引き継ぎ",
            "meeting",
        ],
    ),
    (
        "scope_commercial",
        "Scope/commercial context",
        [
            "契約",
            "契約書",
            "見積",
            "見積書",
            "積算",
            "納品",
            "納品書",
            "検収",
            "検収書",
            "請求",
            "請求書",
            "利用契約",
            "承認申請",
            "協定",
            "覚書",
        ],
    ),
]


@dataclass(frozen=True)
class Candidate:
    group: str
    group_label: str
    path: str
    modified: str
    size: int
    extension: str
    score: int
    reasons: list[str]


def normalized_text(value: str) -> str:
    return unicodedata.normalize("NFKC", value).casefold()


def iter_files(root: Path) -> Iterable[Path]:
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [
            dirname
            for dirname in dirnames
            if not dirname.startswith(".") and dirname not in {"node_modules", "__pycache__"}
        ]
        for filename in filenames:
            if filename.startswith(".") or filename.startswith("~$"):
                continue
            yield Path(dirpath) / filename


def score_group(search_text: str, keywords: list[str]) -> tuple[int, list[str]]:
    reasons: list[str] = []
    score = 0
    for keyword in keywords:
        folded_keyword = normalized_text(keyword)
        if folded_keyword in search_text:
            reasons.append(keyword)
            score += 3 if len(folded_keyword) >= 4 else 1
    return score, reasons


def classify(path: Path, root: Path, include_all: bool) -> Candidate | None:
    try:
        stat = path.stat()
    except (FileNotFoundError, OSError, PermissionError):
        return None
    if not stat_module.S_ISREG(stat.st_mode):
        return None
    rel_path = path.relative_to(root).as_posix()
    extension = path.suffix.casefold()
    search_text = normalized_text(rel_path)

    best_key = "other"
    best_label = "Other document-like files"
    best_score = 0
    best_reasons: list[str] = []
    for key, label, keywords in GROUPS:
        score, reasons = score_group(search_text, keywords)
        if score > best_score:
            best_key = key
            best_label = label
            best_score = score
            best_reasons = reasons

    is_document = extension in DOCUMENT_EXTS
    is_low_signal = extension in LOW_SIGNAL_EXTS
    if not is_document and not include_all and not (is_low_signal and best_score > 0):
        return None
    if is_low_signal and not include_all and best_score == 0:
        return None

    modified = datetime.fromtimestamp(stat.st_mtime).astimezone().strftime("%Y-%m-%d %H:%M:%S %z")
    return Candidate(
        group=best_key,
        group_label=best_label,
        path=rel_path,
        modified=modified,
        size=stat.st_size,
        extension=extension,
        score=best_score,
        reasons=best_reasons,
    )


def grouped_candidates(candidates: list[Candidate]) -> dict[str, list[Candidate]]:
    grouped: dict[str, list[Candidate]] = {key: [] for key, _, _ in GROUPS}
    grouped["other"] = []
    for candidate in candidates:
        grouped.setdefault(candidate.group, []).append(candidate)
    for values in grouped.values():
        values.sort(key=lambda item: (item.score, item.modified, item.path), reverse=True)
    return grouped


def print_markdown(grouped: dict[str, list[Candidate]], max_per_group: int) -> None:
    labels = {key: label for key, label, _ in GROUPS}
    labels["other"] = "Other document-like files"
    print("Based only on filenames, paths, extensions, sizes, and modified times.")
    for key in [*labels.keys()]:
        values = grouped.get(key, [])
        if not values:
            continue
        shown = values if max_per_group <= 0 else values[:max_per_group]
        suffix = "" if len(shown) == len(values) else f" (showing {len(shown)} of {len(values)})"
        print(f"\n## {labels[key]}{suffix}\n")
        print("| Modified | Size | Path | Reason |")
        print("|---|---:|---|---|")
        for item in shown:
            reasons = ", ".join(item.reasons) if item.reasons else "document-like extension"
            print(f"| {item.modified} | {item.size} | `{item.path}` | {reasons} |")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="Source folder to inspect")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of Markdown")
    parser.add_argument(
        "--max-per-group",
        type=int,
        default=40,
        help="Maximum rows per group in Markdown output; 0 means no limit",
    )
    parser.add_argument(
        "--include-all",
        action="store_true",
        help="Include low-signal document-like files such as images, scripts, SQL, audio, and video",
    )
    args = parser.parse_args()

    root = args.source.expanduser().resolve()
    if not root.is_dir():
        raise SystemExit(f"source is not a directory: {root}")

    candidates = [
        candidate
        for path in iter_files(root)
        if (candidate := classify(path, root, args.include_all)) is not None
    ]
    grouped = grouped_candidates(candidates)

    if args.json:
        print(json.dumps({key: [asdict(item) for item in values] for key, values in grouped.items()}, ensure_ascii=False, indent=2))
    else:
        print_markdown(grouped, args.max_per_group)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
