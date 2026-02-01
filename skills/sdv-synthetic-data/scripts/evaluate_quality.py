#!/usr/bin/env python3
"""
合成データの品質評価スクリプト

使用方法:
    python evaluate_quality.py real.csv synthetic.csv
    python evaluate_quality.py real.xlsx synthetic.xlsx --output report.html
    python evaluate_quality.py real.csv synthetic.csv --diagnostic
    python evaluate_quality.py real.csv synthetic.csv --diagnostic-output diagnostic.html

対応形式: CSV (.csv), Excel (.xlsx, .xls), JSON (.json)
"""

import argparse
import sys

from _sdv_utils import read_data


def ask_yes_no(prompt: str) -> bool:
    if not sys.stdin.isatty():
        return False
    try:
        answer = input(prompt).strip().lower()
    except EOFError:
        return False
    return answer in {'y', 'yes'}


def main():
    parser = argparse.ArgumentParser(description='合成データの品質を評価')
    parser.add_argument('real', type=str, help='実データファイル (.csv, .xlsx, .xls, .json)')
    parser.add_argument('synthetic', type=str, help='合成データファイル (.csv, .xlsx, .xls, .json)')
    parser.add_argument('--output', type=str, default=None, help='HTMLレポート出力先')
    parser.add_argument('--diagnostic', action='store_true', help='診断レポートを出力する')
    parser.add_argument('--diagnostic-output', type=str, default=None, help='診断レポート出力先')
    args = parser.parse_args()

    # SDVインポート
    try:
        from sdv.evaluation.single_table import evaluate_quality, run_diagnostic
        from sdv.metadata import Metadata
    except ImportError:
        print("エラー: SDVがインストールされていません")
        print("インストール: pip install sdv")
        return

    # データ読み込み
    real_data = read_data(args.real)
    synthetic_data = read_data(args.synthetic)

    # メタデータ検出
    metadata = Metadata.detect_from_dataframe(real_data)

    # 診断レポート（必要時のみ）
    want_diagnostic = args.diagnostic or args.diagnostic_output is not None
    if not want_diagnostic:
        want_diagnostic = ask_yes_no("診断レポートを出力しますか？ [y/N]: ")

    if want_diagnostic:
        diagnostic = run_diagnostic(
            real_data=real_data,
            synthetic_data=synthetic_data,
            metadata=metadata
        )
        diagnostic_score = None
        if hasattr(diagnostic, 'get_score'):
            try:
                diagnostic_score = diagnostic.get_score()
            except Exception:
                diagnostic_score = None
        if diagnostic_score is not None:
            print(f"診断スコア: {diagnostic_score:.2%}")
        else:
            print("診断レポートを生成しました")

        if args.diagnostic_output:
            try:
                if hasattr(diagnostic, 'save'):
                    diagnostic.save(args.diagnostic_output)
                    print(f"診断レポート保存: {args.diagnostic_output}")
            except Exception as e:
                print(f"診断レポート保存エラー: {e}")

    # 品質レポート
    quality_report = evaluate_quality(
        real_data=real_data,
        synthetic_data=synthetic_data,
        metadata=metadata
    )

    overall_score = quality_report.get_score()
    print(f"総合スコア: {overall_score:.2%}")

    # HTMLレポート保存（オプション）
    if args.output:
        # SDVの組み込みレポート機能を使用
        try:
            quality_report.save(args.output)
            print(f"レポート保存: {args.output}")
        except Exception as e:
            print(f"レポート保存エラー: {e}")
            # フォールバック: テキストレポート
            with open(args.output.replace('.html', '.txt'), 'w') as f:
                f.write(f"総合スコア: {overall_score:.2%}\n")
            print(f"テキストレポート保存: {args.output.replace('.html', '.txt')}")

if __name__ == '__main__':
    main()
