#!/usr/bin/env python3
"""
Analyze files in a directory and collect metadata for grouping.

This script collects file metadata including:
- File path, name, extension
- Creation time, modification time, access time
- File size
- Temporal clustering information (for detecting files updated in sequence)
"""

import os
import json
import argparse
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any
import hashlib


def get_file_info(file_path: Path) -> Dict[str, Any]:
    """Extract metadata from a file."""
    stat = file_path.stat()

    return {
        "path": str(file_path.absolute()),
        "name": file_path.name,
        "stem": file_path.stem,
        "extension": file_path.suffix.lower(),
        "size": stat.st_size,
        "created": stat.st_birthtime,
        "modified": stat.st_mtime,
        "accessed": stat.st_atime,
        "created_iso": datetime.fromtimestamp(stat.st_birthtime).isoformat(),
        "modified_iso": datetime.fromtimestamp(stat.st_mtime).isoformat(),
        "accessed_iso": datetime.fromtimestamp(stat.st_atime).isoformat(),
    }


def analyze_temporal_clusters(files: List[Dict[str, Any]], time_threshold: int = 3600) -> List[Dict[str, Any]]:
    """
    Group files by temporal proximity (files modified close in time).

    Args:
        files: List of file info dictionaries
        time_threshold: Maximum time difference in seconds to consider files as part of the same cluster (default: 1 hour)

    Returns:
        Updated files list with cluster_id added
    """
    if not files:
        return files

    # Sort by modification time
    sorted_files = sorted(files, key=lambda f: f["modified"])

    cluster_id = 0
    sorted_files[0]["cluster_id"] = cluster_id

    for i in range(1, len(sorted_files)):
        time_diff = sorted_files[i]["modified"] - sorted_files[i-1]["modified"]

        if time_diff > time_threshold:
            cluster_id += 1

        sorted_files[i]["cluster_id"] = cluster_id

    return sorted_files


def analyze_directory(directory: str, recursive: bool = False, time_threshold: int = 3600) -> Dict[str, Any]:
    """
    Analyze all files in a directory.

    Args:
        directory: Path to the directory to analyze
        recursive: Whether to recursively analyze subdirectories
        time_threshold: Time threshold for temporal clustering in seconds

    Returns:
        Dictionary containing analysis results
    """
    dir_path = Path(directory).expanduser().resolve()

    if not dir_path.exists():
        raise ValueError(f"Directory does not exist: {directory}")

    if not dir_path.is_dir():
        raise ValueError(f"Path is not a directory: {directory}")

    files = []

    # Collect file information
    if recursive:
        for file_path in dir_path.rglob("*"):
            if file_path.is_file():
                try:
                    files.append(get_file_info(file_path))
                except Exception as e:
                    print(f"Warning: Could not process {file_path}: {e}")
    else:
        for file_path in dir_path.iterdir():
            if file_path.is_file():
                try:
                    files.append(get_file_info(file_path))
                except Exception as e:
                    print(f"Warning: Could not process {file_path}: {e}")

    # Analyze temporal clusters
    files = analyze_temporal_clusters(files, time_threshold)

    # Calculate statistics
    total_size = sum(f["size"] for f in files)
    extensions = {}
    for f in files:
        ext = f["extension"] or "(no extension)"
        extensions[ext] = extensions.get(ext, 0) + 1

    clusters = {}
    for f in files:
        cid = f["cluster_id"]
        if cid not in clusters:
            clusters[cid] = []
        clusters[cid].append(f["name"])

    return {
        "directory": str(dir_path),
        "analyzed_at": datetime.now().isoformat(),
        "file_count": len(files),
        "total_size": total_size,
        "total_size_mb": round(total_size / (1024 * 1024), 2),
        "extensions": extensions,
        "temporal_clusters": {
            str(k): v for k, v in clusters.items()
        },
        "cluster_count": len(clusters),
        "files": files,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Analyze files in a directory for organization"
    )
    parser.add_argument(
        "directory",
        help="Directory to analyze"
    )
    parser.add_argument(
        "-r", "--recursive",
        action="store_true",
        help="Recursively analyze subdirectories"
    )
    parser.add_argument(
        "-t", "--time-threshold",
        type=int,
        default=3600,
        help="Time threshold for temporal clustering in seconds (default: 3600 = 1 hour)"
    )
    parser.add_argument(
        "-o", "--output",
        help="Output JSON file (default: print to stdout)"
    )

    args = parser.parse_args()

    try:
        result = analyze_directory(
            args.directory,
            recursive=args.recursive,
            time_threshold=args.time_threshold
        )

        output_json = json.dumps(result, indent=2, ensure_ascii=False)

        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(output_json)
            print(f"Analysis saved to: {args.output}")
        else:
            print(output_json)

    except Exception as e:
        print(f"Error: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
