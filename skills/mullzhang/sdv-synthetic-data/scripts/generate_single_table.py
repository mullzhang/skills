#!/usr/bin/env python3
"""
Single-table synthetic data generation script.

Usage:
    python generate_single_table.py input.csv output.csv --rows 1000
    python generate_single_table.py input.xlsx output.xlsx --rows 1000 --synthesizer ctgan
    python generate_single_table.py input.json output.json --rows 1000

Supported formats: CSV (.csv), Excel (.xlsx, .xls), JSON (.json)
"""

import argparse
from pathlib import Path

from _sdv_utils import apply_seed, read_data, sample_with_seed, write_data


def main():
    parser = argparse.ArgumentParser(description='Generate single-table synthetic data with SDV')
    parser.add_argument('input', type=str, help='Input file path (.csv, .xlsx, .xls, .json)')
    parser.add_argument('output', type=str, help='Output file path (.csv, .xlsx, .xls, .json)')
    parser.add_argument('--rows', type=int, default=None, help='Number of rows to generate (default: same as input)')
    parser.add_argument('--synthesizer', type=str, default='gaussian',
                        choices=['gaussian', 'ctgan', 'tvae', 'copulagan'],
                        help='Synthesizer to use (default: gaussian)')
    parser.add_argument('--epochs', type=int, default=300, help='Epochs for CTGAN/TVAE/CopulaGAN')
    parser.add_argument('--seed', type=int, default=None, help='Seed value for reproducibility (default: none)')
    parser.add_argument('--save-model', nargs='?', const='__default__', default=None,
                        help='Save trained model (auto-generate path from output filename if omitted)')
    parser.add_argument('--save-metadata', nargs='?', const='__default__', default=None,
                        help='Save metadata (auto-generate path from output filename if omitted)')
    args = parser.parse_args()

    # SDV import (lazy import for clearer error messages)
    try:
        from sdv.single_table import (
            GaussianCopulaSynthesizer,
            CTGANSynthesizer,
            TVAESynthesizer,
            CopulaGANSynthesizer
        )
        from sdv.metadata import Metadata
    except ImportError:
        print("Error: SDV is not installed")
        print("Install: pip install sdv")
        return

    # Load data
    data = read_data(args.input)

    # Detect metadata
    metadata = Metadata.detect_from_dataframe(data)

    # Select synthesizer
    if args.synthesizer == 'gaussian':
        synthesizer = GaussianCopulaSynthesizer(metadata)
    elif args.synthesizer == 'ctgan':
        synthesizer = CTGANSynthesizer(metadata, epochs=args.epochs)
    elif args.synthesizer == 'tvae':
        synthesizer = TVAESynthesizer(metadata, epochs=args.epochs)
    elif args.synthesizer == 'copulagan':
        synthesizer = CopulaGANSynthesizer(metadata, epochs=args.epochs)

    # Train (set seed before fitting for reproducibility)
    if args.seed is not None:
        apply_seed(args.seed, synthesizer)
    synthesizer.fit(data)

    # Generate
    num_rows = args.rows if args.rows else len(data)
    if args.seed is not None:
        apply_seed(args.seed, synthesizer)
    synthetic_data = sample_with_seed(synthesizer, num_rows=num_rows, seed=args.seed)

    # Save synthetic data
    write_data(synthetic_data, args.output)

    # Build default save paths from output filename
    output_path = Path(args.output)
    default_model_path = output_path.parent / f"{output_path.stem}.sdv.pkl"
    default_metadata_path = output_path.parent / f"{output_path.stem}.metadata.json"

    save_metadata = args.save_metadata is not None
    save_model = args.save_model is not None

    # Save metadata (optional)
    if save_metadata:
        if args.save_metadata in (None, '__default__'):
            metadata_path = str(default_metadata_path)
        else:
            metadata_path = args.save_metadata
        metadata.save_to_json(metadata_path)

    # Save model (optional)
    if save_model:
        if args.save_model in (None, '__default__'):
            model_path = str(default_model_path)
        else:
            model_path = args.save_model
        synthesizer.save(model_path)
    print("Done")


if __name__ == '__main__':
    main()
