#!/usr/bin/env python3
"""
単一テーブルの合成データ生成スクリプト

使用方法:
    python generate_single_table.py input.csv output.csv --rows 1000
    python generate_single_table.py input.xlsx output.xlsx --rows 1000 --synthesizer ctgan
    python generate_single_table.py input.json output.json --rows 1000

対応形式: CSV (.csv), Excel (.xlsx, .xls), JSON (.json)
"""

import argparse
from pathlib import Path

from _sdv_utils import apply_seed, read_data, sample_with_seed, write_data


def main():
    parser = argparse.ArgumentParser(description='SDVで単一テーブルの合成データを生成')
    parser.add_argument('input', type=str, help='入力ファイルパス (.csv, .xlsx, .xls, .json)')
    parser.add_argument('output', type=str, help='出力ファイルパス (.csv, .xlsx, .xls, .json)')
    parser.add_argument('--rows', type=int, default=None, help='生成する行数（デフォルト: 入力と同じ）')
    parser.add_argument('--synthesizer', type=str, default='gaussian',
                        choices=['gaussian', 'ctgan', 'tvae', 'copulagan'],
                        help='使用するシンセサイザー（デフォルト: gaussian）')
    parser.add_argument('--epochs', type=int, default=300, help='CTGAN/TVAE/CopulaGANのエポック数')
    parser.add_argument('--seed', type=int, default=None, help='再現性のためのシード値（デフォルト: なし）')
    parser.add_argument('--save-model', nargs='?', const='__default__', default=None,
                        help='学習済みモデルを保存（パス未指定時は出力ファイル名から自動生成）')
    parser.add_argument('--save-metadata', nargs='?', const='__default__', default=None,
                        help='メタデータを保存（パス未指定時は出力ファイル名から自動生成）')
    args = parser.parse_args()

    # SDVインポート（遅延インポートでエラーメッセージを明確に）
    try:
        from sdv.single_table import (
            GaussianCopulaSynthesizer,
            CTGANSynthesizer,
            TVAESynthesizer,
            CopulaGANSynthesizer
        )
        from sdv.metadata import Metadata
    except ImportError:
        print("エラー: SDVがインストールされていません")
        print("インストール: pip install sdv")
        return

    # データ読み込み
    data = read_data(args.input)

    # メタデータ検出
    metadata = Metadata.detect_from_dataframe(data)

    # シンセサイザー選択
    if args.synthesizer == 'gaussian':
        synthesizer = GaussianCopulaSynthesizer(metadata)
    elif args.synthesizer == 'ctgan':
        synthesizer = CTGANSynthesizer(metadata, epochs=args.epochs)
    elif args.synthesizer == 'tvae':
        synthesizer = TVAESynthesizer(metadata, epochs=args.epochs)
    elif args.synthesizer == 'copulagan':
        synthesizer = CopulaGANSynthesizer(metadata, epochs=args.epochs)

    # 学習（再現性のためシードは学習前に設定）
    if args.seed is not None:
        apply_seed(args.seed, synthesizer)
    synthesizer.fit(data)

    # 生成
    num_rows = args.rows if args.rows else len(data)
    if args.seed is not None:
        apply_seed(args.seed, synthesizer)
    synthetic_data = sample_with_seed(synthesizer, num_rows=num_rows, seed=args.seed)

    # 保存
    write_data(synthetic_data, args.output)

    # 出力ファイル名からデフォルト保存先を作成
    output_path = Path(args.output)
    default_model_path = output_path.parent / f"{output_path.stem}.sdv.pkl"
    default_metadata_path = output_path.parent / f"{output_path.stem}.metadata.json"

    save_metadata = args.save_metadata is not None
    save_model = args.save_model is not None

    # メタデータ保存（オプション）
    if save_metadata:
        if args.save_metadata in (None, '__default__'):
            metadata_path = str(default_metadata_path)
        else:
            metadata_path = args.save_metadata
        metadata.save_to_json(metadata_path)

    # モデル保存（オプション）
    if save_model:
        if args.save_model in (None, '__default__'):
            model_path = str(default_model_path)
        else:
            model_path = args.save_model
        synthesizer.save(model_path)
    print("完了")

if __name__ == '__main__':
    main()
