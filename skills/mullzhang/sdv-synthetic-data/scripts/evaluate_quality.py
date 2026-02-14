#!/usr/bin/env python3
"""
Synthetic data quality evaluation script.

Usage:
    python evaluate_quality.py real.csv synthetic.csv
    python evaluate_quality.py real.xlsx synthetic.xlsx --output report.html
    python evaluate_quality.py real.csv synthetic.csv --diagnostic
    python evaluate_quality.py real.csv synthetic.csv --diagnostic-output diagnostic.html

Supported formats: CSV (.csv), Excel (.xlsx, .xls), JSON (.json)
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
    parser = argparse.ArgumentParser(description='Evaluate synthetic data quality')
    parser.add_argument('real', type=str, help='Real data file (.csv, .xlsx, .xls, .json)')
    parser.add_argument('synthetic', type=str, help='Synthetic data file (.csv, .xlsx, .xls, .json)')
    parser.add_argument('--output', type=str, default=None, help='HTML report output path')
    parser.add_argument('--diagnostic', action='store_true', help='Generate a diagnostic report')
    parser.add_argument('--diagnostic-output', type=str, default=None, help='Diagnostic report output path')
    args = parser.parse_args()

    # Import SDV
    try:
        from sdv.evaluation.single_table import evaluate_quality, run_diagnostic
        from sdv.metadata import Metadata
    except ImportError:
        print("Error: SDV is not installed")
        print("Install: pip install sdv")
        return

    # Load data
    real_data = read_data(args.real)
    synthetic_data = read_data(args.synthetic)

    # Detect metadata
    metadata = Metadata.detect_from_dataframe(real_data)

    # Diagnostic report (only when requested)
    want_diagnostic = args.diagnostic or args.diagnostic_output is not None
    if not want_diagnostic:
        want_diagnostic = ask_yes_no("Generate a diagnostic report? [y/N]: ")

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
            print(f"Diagnostic score: {diagnostic_score:.2%}")
        else:
            print("Diagnostic report generated")

        if args.diagnostic_output:
            try:
                if hasattr(diagnostic, 'save'):
                    diagnostic.save(args.diagnostic_output)
                    print(f"Diagnostic report saved: {args.diagnostic_output}")
            except Exception as e:
                print(f"Error saving diagnostic report: {e}")

    # Quality report
    quality_report = evaluate_quality(
        real_data=real_data,
        synthetic_data=synthetic_data,
        metadata=metadata
    )

    overall_score = quality_report.get_score()
    print(f"Overall score: {overall_score:.2%}")

    # Save HTML report (optional)
    if args.output:
        # Use SDV's built-in report save functionality
        try:
            quality_report.save(args.output)
            print(f"Report saved: {args.output}")
        except Exception as e:
            print(f"Error saving report: {e}")
            # Fallback: text report
            with open(args.output.replace('.html', '.txt'), 'w') as f:
                f.write(f"Overall score: {overall_score:.2%}\n")
            print(f"Text report saved: {args.output.replace('.html', '.txt')}")


if __name__ == '__main__':
    main()
