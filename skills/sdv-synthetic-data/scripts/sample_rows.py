#!/usr/bin/env python3
"""
行数または割合を指定してデータをサンプリングするスクリプト。

使用方法:
    python sample_rows.py input.csv output.csv --rows 1000
    python sample_rows.py input.csv output.csv --rows 2000 --replace
    python sample_rows.py input.xlsx output.xlsx --rows 1000 --seed 42
    python sample_rows.py input.xlsx output.xlsx --rows 1000 --sheet Sheet1
    python sample_rows.py input.csv output.csv --fraction 0.1
    python sample_rows.py input.json output.json --rows 1000

対応形式: CSV (.csv), Excel (.xlsx, .xls), JSON (.json)
"""

import argparse
from pathlib import Path
from typing import Optional

import pandas as pd

from _sdv_utils import SUPPORTED_EXTENSIONS, write_data


def read_data(file_path: str, sheet_name: Optional[str] = None) -> pd.DataFrame:
    """ファイル拡張子に応じてデータを読み込む（Excelはシート指定可）"""
    ext = Path(file_path).suffix.lower()
    if ext == '.csv':
        return pd.read_csv(file_path)
    if ext in ('.xlsx', '.xls'):
        if sheet_name:
            return pd.read_excel(file_path, sheet_name=sheet_name)
        return pd.read_excel(file_path)
    if ext == '.json':
        return pd.read_json(file_path)
    raise ValueError(f"未対応のファイル形式: {ext} (対応形式: {SUPPORTED_EXTENSIONS})")


def main() -> None:
    parser = argparse.ArgumentParser(description='行数または割合を指定してデータをサンプリング')
    parser.add_argument('input', type=str, help='入力ファイルパス (.csv, .xlsx, .xls, .json)')
    parser.add_argument('output', type=str, help='出力ファイルパス (.csv, .xlsx, .xls, .json)')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--rows', type=int, help='抽出する行数')
    group.add_argument('--fraction', '--frac', type=float, help='抽出する割合 (0 < fraction <= 1)')
    parser.add_argument('--seed', type=int, default=None, help='再現性のためのシード値')
    parser.add_argument('--replace', action='store_true', help='復元抽出を行う')
    parser.add_argument('--sheet', type=str, default=None, help='Excelのシート名（任意）')
    args = parser.parse_args()

    if args.rows is not None and args.rows <= 0:
        raise ValueError('--rows は1以上を指定してください')
    if args.fraction is not None and not (0 < args.fraction <= 1):
        raise ValueError('--fraction は0より大きく1以下を指定してください')

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

    print(f"完了: 入力行数={len(data)}, 出力行数={len(sampled)}")


if __name__ == "__main__":
    main()
