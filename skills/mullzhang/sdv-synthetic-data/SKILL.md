---
name: sdv-synthetic-data
description: "Generate synthetic data with SDV (Synthetic Data Vault). Learn patterns from real data with machine learning and produce privacy-preserving synthetic data. Use cases: (1) single-table synthetic data generation, (2) multi-table (relational DB) synthetic data generation, (3) time-series synthetic data generation, (4) synthetic data quality evaluation, and (5) metadata and constraint setup"
---

# SDV Synthetic Data Generation

Use SDV (Synthetic Data Vault) to generate high-quality synthetic data that learns patterns from real data.

---

## **Most Important: Data Privacy Restrictions**

**Always read this section first and strictly follow the rules below.**

### Prohibited Actions (Never Do These)

1. **Do not read data files with the `Read` tool**
   - Restricted extensions: `.csv`, `.xlsx`, `.xls`, `.json`, `.pkl`, `.html`, `.txt`
   - Do not inspect or display the user's data content
   - Do not inspect generated synthetic data content either

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

Follow these steps when generating synthetic data.
All scripts accept options as runtime arguments, so complete all confirmations in Steps 1 to 4 before executing Step 5.

1. **Confirm number of rows**: Ask the user how many rows to generate (`num_rows`). Use the `AskUserQuestion` tool with the following prompt:
   - Question: "How many rows of synthetic data should be generated?"
   - Header: "Row Count"
   - Options:
     - "Same as source data (Recommended)" - Generate the same number of rows as the source data
     - "1,000 rows" - Generate 1,000 rows
     - "10,000 rows" - Generate 10,000 rows
     - "100,000 rows" - Generate 100,000 rows
   - If the user selects "Other", use the numeric value they enter

2. **Confirm seed value**: Confirm the seed value (`seed`) for reproducibility. Use the `AskUserQuestion` tool with the following prompt:
   - Question: "Do you want to specify a seed value for reproducibility?"
   - Header: "Seed Value"
   - Options:
     - "Do not specify (Random) (Recommended)" - Generate randomly without a seed
     - "42" - Use seed 42 (common default)
     - "123" - Use seed 123
     - "0" - Use seed 0
   - If the user selects "Other", use the numeric value they enter
   - If a seed is provided, set random seeds and pass it only when `sample` supports the `seed` argument (see script implementation)

3. **Select synthesizer**: Confirm the synthesizer type if needed

4. **Confirm model and metadata saving**: Ask whether trained artifacts should be saved for reuse. Use the `AskUserQuestion` tool with the following prompt:
   - Question: "Do you want to save the trained synthesizer and metadata?"
   - Header: "Model Save"
   - Options:
     - "Save both (Recommended)" - Save both synthesizer and metadata
     - "Synthesizer only" - Save trained synthesizer only
     - "Do not save" - Finish without saving
   - See script options (`--save-model`, `--save-metadata`) for save/load details

5. **Generate data**: Execute scripts by passing all confirmed options from Steps 1 to 4 (row count, seed value, synthesizer, save settings) as arguments

## Quick Start

Use `scripts/generate_single_table.py` to generate synthetic data for a single table.
**Note**: Scripts exist under `.codex/skills/sdv-synthetic-data/scripts/`. Do not create new scripts; execute existing scripts directly (example: `uv run python .codex/skills/sdv-synthetic-data/scripts/generate_single_table.py ...`).

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

Time-series generation is currently unsupported by existing scripts. Add a new script if needed.

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
