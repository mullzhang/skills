#!/usr/bin/env python3
"""
Sample data by row count or fraction.

Usage:
    python sample_rows.py input.csv output.csv --rows 1000
    python sample_rows.py input.csv output.csv --rows 2000 --replace
    python sample_rows.py input.xlsx output.xlsx --rows 1000 --seed 42
    python sample_rows.py input.xlsx output.xlsx --rows 1000 --sheet Sheet1
    python sample_rows.py input.csv output.csv --fraction 0.1
    python sample_rows.py input.json output.json --rows 1000

Supported formats: CSV (.csv), Excel (.xlsx, .xls), JSON (.json)
"""

import argparse
from pathlib import Path
from typing import Optional

import pandas as pd

from _sdv_utils import SUPPORTED_EXTENSIONS, write_data


def read_data(file_path: str, sheet_name: Optional[str] = None) -> pd.DataFrame:
    """Read data based on file extension (Excel supports optional sheet selection)."""
    ext = Path(file_path).suffix.lower()
    if ext == '.csv':
        return pd.read_csv(file_path)
    if ext in ('.xlsx', '.xls'):
        if sheet_name:
            return pd.read_excel(file_path, sheet_name=sheet_name)
        return pd.read_excel(file_path)
    if ext == '.json':
        return pd.read_json(file_path)
    raise ValueError(f"Unsupported file format: {ext} (supported: {SUPPORTED_EXTENSIONS})")


def main() -> None:
    parser = argparse.ArgumentParser(description='Sample data by row count or fraction')
    parser.add_argument('input', type=str, help='Input file path (.csv, .xlsx, .xls, .json)')
    parser.add_argument('output', type=str, help='Output file path (.csv, .xlsx, .xls, .json)')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--rows', type=int, help='Number of rows to sample')
    group.add_argument('--fraction', '--frac', type=float, help='Fraction to sample (0 < fraction <= 1)')
    parser.add_argument('--seed', type=int, default=None, help='Seed value for reproducibility')
    parser.add_argument('--replace', action='store_true', help='Sample with replacement')
    parser.add_argument('--sheet', type=str, default=None, help='Excel sheet name (optional)')
    args = parser.parse_args()

    if args.rows is not None and args.rows <= 0:
        raise ValueError('--rows must be 1 or greater')
    if args.fraction is not None and not (0 < args.fraction <= 1):
        raise ValueError('--fraction must be greater than 0 and less than or equal to 1')

    data = read_data(args.input, sheet_name=args.sheet)

    if args.rows is not None:
        if args.replace:
            sampled = data.sample(n=args.rows, replace=True, random_state=args.seed)
        elif args.rows >= len(data):
            sampled = data.copy()
        else:
            sampled = data.sample(n=args.rows, random_state=args.seed)
    else:
        sampled = data.sample(frac=args.fraction, replace=args.replace, random_state=args.seed)

    sampled = sampled.reset_index(drop=True)
    write_data(sampled, args.output)

    print(f"Done: input_rows={len(data)}, output_rows={len(sampled)}")


if __name__ == "__main__":
    main()
