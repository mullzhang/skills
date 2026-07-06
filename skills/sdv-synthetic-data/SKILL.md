---
name: sdv-synthetic-data
description: "Generate synthetic data with SDV (Synthetic Data Vault) using bundled scripts, without ever reading the user's data content. Use cases: (1) single-table synthetic data generation, (2) multi-table (relational DB) synthetic data generation, (3) synthetic data quality evaluation, and (4) metadata and constraint setup. Time-series generation has no bundled script and requires writing a custom SDV script."
---

# SDV Synthetic Data Generation

Use SDV (Synthetic Data Vault) to generate high-quality synthetic data that learns patterns from real data.

---

## **Most Important: Data Privacy Restrictions**

**Always read this section first and strictly follow the rules below.**

### Prohibited Actions (Never Do These)

1. **Do not read data content**
   - Never open the user's input data or the generated synthetic data with the `Read` tool or shell commands (`cat`, `head`, etc.), regardless of extension (`.csv`, `.xlsx`, `.xls`, `.json`, `.pkl`)
   - This restriction is about data rows, not file types: metadata JSON, config files, and quality/diagnostic reports (`.html`, `.txt`) contain structure and scores, not row values, so reading them is allowed and needed for the workflow

2. **Do not generate data preview code**
   - Do not include `print(data)`, `print(df)`, `data.head()`, `data.tail()`, `data.sample()`, etc.

3. **Do not log actual data values**

### No Pre-Inspection of Data Is Required

The scripts automatically detect data structure, so **do not inspect data file contents or schema in advance**.
Follow the workflow, ask the user only for required confirmations (number of rows, seed value, etc.), and run the scripts directly.

---

## Supported File Formats

### Data Input (Supported Formats)

| Format | Extension | Read Method |
|------|--------|-------------|
| CSV | `.csv` | `pd.read_csv()` |
| Excel | `.xlsx`, `.xls` | `pd.read_excel()` |
| JSON | `.json` | `pd.read_json()` |

### SDV Output Files

| File Type | Extension | Description |
|-------------|--------|------|
| Synthetic data | `.csv`, `.xlsx`, `.json` | Generated synthetic data |
| Synthesizer | `.pkl` | Trained model |
| Metadata | `.json` | Data structure definition |
| Quality report | `.html`, `.txt` | Evaluation report |

## Execution Environment Check and Run Method

This skill should **check the Python environment of the target project and run scripts in that environment**.

Guideline (priority order):
- If `uv.lock` or `pyproject.toml` exists, prioritize the `uv` environment and run with `uv run python scripts/...`
- If `.venv/` exists, use that virtual environment's Python (example: `.venv/bin/python scripts/...`)
- If neither exists, ask the user which environment should be used

Always choose execution commands to match the **target project's environment** (uv/venv/poetry/pipenv, etc.).

## Workflow

Confirm the run parameters with the user first, then execute the bundled script once with all options set. Skip any point the user has already specified in their request. Confirm the remaining points (use `AskUserQuestion` with multiple questions in one call when the tool is available; otherwise ask in chat, presenting the default as the recommended option):

1. **Row count** (`--rows`): default is the same row count as the source data.
2. **Seed** (`--seed`): default is random (no seed); offer a fixed seed for reproducibility.
3. **Synthesizer** (`--synthesizer`): default `gaussian`; see the selection table below. Skip asking when the default is clearly appropriate.
4. **Saving artifacts** (`--save-model`, `--save-metadata`): recommend saving both the trained synthesizer and metadata for reuse.

## Quick Start

Use `scripts/generate_single_table.py` to generate synthetic data for a single table.
**Note**: Run the bundled scripts from this skill's own `scripts/` directory (the directory containing this SKILL.md, wherever the skill is installed). Do not write new scripts for supported cases; execute the existing ones directly (example: `uv run python <path-to-this-skill>/scripts/generate_single_table.py input.csv output.csv --rows 1000`).

## Synthesizer Selection

| Synthesizer | Characteristics | Recommended Use |
|---|---|---|
| `GaussianCopulaSynthesizer` | Fast, transparent, customizable | **Default choice** |
| `CTGANSynthesizer` | Uses GAN, high fidelity | More complex patterns |
| `TVAESynthesizer` | Uses VAE, high fidelity | Complex patterns |
| `CopulaGANSynthesizer` | GaussianCopula + CTGAN | Hybrid |

For exact selection behavior, refer to the `--synthesizer` option in `generate_single_table.py`.

## Metadata Configuration

### Auto Detection
`generate_single_table.py` and `generate_multi_table.py` use `Metadata.detect_from_dataframe(...)`.

### Manual Configuration
If manual adjustment is needed, save metadata with `--save-metadata`, edit it, and load it later.

### sdtype List
- `numerical`: Numeric
- `datetime`: Datetime (`datetime_format` required)
- `categorical`: Categorical
- `boolean`: Boolean
- `id`: Identifier (`regex_format` can define patterns)
- `email`, `phone_number`, `ssn`, etc.: PII auto-anonymization

## Constraint Configuration

Add constraints to enforce business rules 100%.

Constraint setup requires metadata edits or additional implementation. Extend scripts when needed.

## Multi-Table (Relational)

Use `generate_multi_table.py`. Specify `tables` and `relationships` in the config file, and control generation volume with `--scale`.

`generate_multi_table.py` auto-detects each table with `metadata.detect_from_dataframe(..., table_name=...)` and applies `primary_key` and `relationships` from the config file. If needed, save metadata with `--save-metadata` and tune it later.

## Time-Series Data

No bundled script covers time-series generation. If the user needs it, write a per-run script using SDV's `PARSynthesizer`, keeping the same privacy restrictions (no data preview, no value logging).

## Quality Evaluation

Use `evaluate_quality.py` for quality evaluation. Diagnostic reports are reviewed at execution time and can be explicitly output with `--diagnostic` or `--diagnostic-output`.

## Model Save/Load

Use each script's `--save-model` / `--save-metadata` options for save/load workflows.

## Scripts

See reusable scripts in `scripts/`:

- `generate_single_table.py`: Single-table synthetic data generation (`--rows`, `--seed`, `--synthesizer`, `--epochs`, `--save-model`, `--save-metadata`)
- `generate_multi_table.py`: Multi-table synthetic data generation (`--config`, `--output-dir`, `--output-format`, `--scale`, `--seed`, `--save-model`, `--save-metadata`)
- `evaluate_quality.py`: Quality report generation (`--output`, `--diagnostic`, `--diagnostic-output`)
- `sample_rows.py`: Sample rows from input data (`--rows` or `--fraction`, `--replace`, `--seed`, `--sheet`)
