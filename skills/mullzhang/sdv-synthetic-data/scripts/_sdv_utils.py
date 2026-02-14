#!/usr/bin/env python3
"""
Shared utilities for sdv-synthetic-data scripts.
"""

import inspect
import random
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

# Supported file extensions
SUPPORTED_EXTENSIONS = {'.csv', '.xlsx', '.xls', '.json'}


def read_data(file_path: str) -> pd.DataFrame:
    """Read data based on file extension."""
    ext = Path(file_path).suffix.lower()
    if ext == '.csv':
        return pd.read_csv(file_path)
    if ext in ('.xlsx', '.xls'):
        return pd.read_excel(file_path)
    if ext == '.json':
        return pd.read_json(file_path)
    raise ValueError(f"Unsupported file format: {ext} (supported: {SUPPORTED_EXTENSIONS})")


def write_data(df: pd.DataFrame, file_path: str) -> None:
    """Write data based on file extension."""
    ext = Path(file_path).suffix.lower()
    if ext == '.csv':
        df.to_csv(file_path, index=False)
        return
    if ext in ('.xlsx', '.xls'):
        df.to_excel(file_path, index=False)
        return
    if ext == '.json':
        df.to_json(file_path, orient='records', force_ascii=False, indent=2)
        return
    raise ValueError(f"Unsupported file format: {ext} (supported: {SUPPORTED_EXTENSIONS})")


def apply_seed(seed: Optional[int], synthesizer=None) -> None:
    """Set random seeds (and apply to synthesizer when possible)."""
    if seed is None:
        return
    np.random.seed(seed)
    random.seed(seed)
    if synthesizer is not None and hasattr(synthesizer, 'set_random_state'):
        try:
            synthesizer.set_random_state(seed)
        except Exception:
            pass


def sample_with_seed(
    synthesizer,
    *,
    num_rows: Optional[int] = None,
    scale: Optional[float] = None,
    seed: Optional[int] = None,
):
    """Pass seed when supported; otherwise sample without it."""
    kwargs = {}
    if num_rows is not None:
        kwargs['num_rows'] = num_rows
    if scale is not None:
        kwargs['scale'] = scale
    if seed is not None:
        try:
            sig = inspect.signature(synthesizer.sample)
            if 'seed' in sig.parameters:
                kwargs['seed'] = seed
        except (TypeError, ValueError):
            pass
    return synthesizer.sample(**kwargs)
