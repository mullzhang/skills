#!/usr/bin/env python3
"""
複数テーブル（リレーショナル）の合成データ生成スクリプト

使用方法:
    python generate_multi_table.py --config schema.json --output-dir ./synthetic
    python generate_multi_table.py --config schema.json --output-dir ./synthetic --scale 2.0 --seed 42

schema.json の例:
{
    "tables": {
        "users": {
            "file": "users.csv",
            "primary_key": "user_id"
        },
        "orders": {
            "file": "orders.xlsx",
            "primary_key": "order_id"
        }
    },
    "relationships": [
        {
            "parent_table": "users",
            "parent_key": "user_id",
            "child_table": "orders",
            "child_key": "user_id"
        }
    ],
    "output_format": "csv"
}

対応形式: CSV (.csv), Excel (.xlsx, .xls), JSON (.json)
"""

import argparse
import json
from pathlib import Path

from _sdv_utils import apply_seed, read_data, sample_with_seed, write_data


def main():
    parser = argparse.ArgumentParser(description='SDVで複数テーブルの合成データを生成')
    parser.add_argument('--config', type=str, required=True, help='スキーマ設定JSONファイル')
    parser.add_argument('--output-dir', type=str, required=True, help='出力ディレクトリ')
    parser.add_argument('--output-format', type=str, default=None,
                        choices=['csv', 'xlsx', 'json'],
                        help='出力形式（デフォルト: 設定ファイルのoutput_formatまたはcsv）')
    parser.add_argument('--scale', type=float, default=1.0, help='データ量のスケール倍率')
    parser.add_argument('--seed', type=int, default=None, help='再現性のためのシード値（デフォルト: なし）')
    parser.add_argument('--save-model', type=str, default=None, help='学習済みモデルの保存先')
    parser.add_argument('--save-metadata', type=str, default=None, help='メタデータの保存先（JSON）')
    args = parser.parse_args()

    # SDVインポート
    try:
        from sdv.multi_table import HMASynthesizer
        from sdv.metadata import Metadata
        from sdv.utils import drop_unknown_references
    except ImportError:
        print("エラー: SDVがインストールされていません")
        print("インストール: pip install sdv")
        return

    # 設定読み込み
    with open(args.config, 'r', encoding='utf-8') as f:
        config = json.load(f)

    config_dir = Path(args.config).parent

    # データ読み込み
    data = {}
    for table_name, table_config in config['tables'].items():
        file_path = config_dir / table_config['file']
        data[table_name] = read_data(str(file_path))

    # メタデータ設定
    metadata = Metadata()

    for table_name, table_config in config['tables'].items():
        metadata.detect_from_dataframe(data=data[table_name], table_name=table_name)
        if 'primary_key' in table_config:
            metadata.set_primary_key(table_name, table_config['primary_key'])

    # リレーションシップ設定
    for rel in config.get('relationships', []):
        metadata.add_relationship(
            parent_table_name=rel['parent_table'],
            parent_primary_key=rel['parent_key'],
            child_table_name=rel['child_table'],
            child_foreign_key=rel['child_key']
        )

    # 参照整合性クリーニング
    cleaned_data = drop_unknown_references(data, metadata)

    # 学習（再現性のためシードは学習前に設定）
    synthesizer = HMASynthesizer(metadata)
    if args.seed is not None:
        apply_seed(args.seed, synthesizer)
    synthesizer.fit(cleaned_data)

    # 生成
    if args.seed is not None:
        apply_seed(args.seed, synthesizer)
    synthetic_data = sample_with_seed(synthesizer, scale=args.scale, seed=args.seed)

    # 出力形式の決定
    output_format = args.output_format or config.get('output_format', 'csv')

    # 出力
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    for table_name, df in synthetic_data.items():
        output_path = output_dir / f"{table_name}.{output_format}"
        write_data(df, str(output_path))

    # メタデータ保存（オプション）
    if args.save_metadata:
        metadata.save_to_json(args.save_metadata)

    # モデル保存（オプション）
    if args.save_model:
        synthesizer.save(args.save_model)

    print("完了")


if __name__ == '__main__':
    main()
