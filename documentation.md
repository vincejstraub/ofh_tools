# 📁 ofh_tools


This directory contains CLI-ready Python scripts for extracting and processing phenotype data from DNAnexus datasets.

---

## 🚀 Available Scripts

### 1. `process_pheno_list.py`

✅ **Description:**  
Merges a raw phenotype list with coding and data dictionary files to produce a cleaned and structured phenotype table.

#### 🧩 Required Arguments
| Argument      | Description                                                               |
|---------------|---------------------------------------------------------------------------|
| `input_file`  | Path to the input CSV. Use `-` to use default from `config.json`          |
| `output_file` | Path to the output CSV to be written                                      |

#### ✅ Default Behavior:
If `-` is passed as the input, the script uses:  
`config["files"]["PHENO_LISTS"]["PHENO_LIST_V1_RAW"]`

#### 💡 Example
```bash
!python ofh_tools/process_pheno_list.py - outputs/pheno_list_v1_processed.csv
```

### 2. `extract_raw_field_vals.py`

✅ **Description:**  
Extracts raw values from a DNAnexus dataset based on a phenotype list, saving the output as a CSV or SQL query.

#### 🧩 Optional Arguments
| Argument       | Default                                 | Description                                                                 |
|----------------|-----------------------------------------|-----------------------------------------------------------------------------|
| `--phenotype`  | `PHENO_LIST_V1_RAW`                     | Key from `config['files']['PHENO_LISTS']`                                   |
| `--output`     | `outputs/pheno_list_v1_raw_values.csv`  | Path to output CSV or SQL                                                   |
| `--cohort`     | `TEST_COHORT`                           | Key from `config['COHORTS']` to select the dataset                          |
| `--dataset`    | _None_                                  | Override with a specific DNAnexus dataset ID (bypasses `--cohort`)          |
| `--sql-only`   | `False`                                 | If set, generates SQL only and saves it to `--output`                       |

#### 💡 Example Usages

Run with default settings:
```bash
!python ofh_tools/extract_raw_field_vals.py
```

Use a different phenotype and cohort:

```bash
!python ofh_tools/extract_raw_field_vals.py --phenotype EXAMPLE_PHENOTYPE_1 --cohort GENOTYPED --output outputs/genotyped.csv
```
Only generate SQL and save to file:
```bash
!python ofh_tools/extract_raw_field_vals.py --sql-only --output outputs/query.sql
```

## 🧠 Notes

- All required file paths and IDs are loaded from `config.json` located in `/mnt/project/helpers/`, or downloaded automatically if not found locally.
- All referenced files (phenotype lists, coding files, data dictionary, etc.) are downloaded using `dx download` if missing.
- Output directories are automatically created if they don’t exist.
- The `.sql` file is only saved when `--sql-only` is explicitly provided.
- Input phenotype lists must include columns named `entity` and `name`.


