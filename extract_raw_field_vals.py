import pandas as pd
import dxdata
import dxpy
import os
import logging
import subprocess
import json
import shutil
import sys
from pathlib import Path

# --- CONFIG CONSTANTS ---
CONFIG_FILENAME = "config.json"
HELPERS_DIR = Path("/mnt/project/helpers")
CONFIG_FILE_ID = "file-J0J2f4k2JqxzxgB3j4yV5G7F"

# --- LOGGING ---
logging.basicConfig(level=logging.INFO)

# --- FILE LOADER WITH LOCAL FALLBACK ---
def load_or_download_file(file_path: Path, file_id: str, description: str = "", validate_json=False):
    def is_valid_json(path: Path):
        try:
            with open(path, "r") as f:
                json.load(f)
            return True
        except Exception as e:
            if not isinstance(e, FileNotFoundError):
                logging.warning(f"Invalid JSON in {path}: {e}")
            return False

    if file_path.exists() and (not validate_json or is_valid_json(file_path)):
        logging.info(f"✅ Using existing {description}: {file_path}")
        return file_path

    # Reconstruct the relative path from /mnt/project to use in notebook space
    project_root = Path("/mnt/project").resolve()
    try:
        relative_path = file_path.resolve().relative_to(project_root)
    except ValueError:
        relative_path = file_path.name  # fallback: flat filename only

    fallback_path = Path(".") / relative_path

    if fallback_path.exists() and (not validate_json or is_valid_json(fallback_path)):
        logging.info(f"✅ Using existing local fallback: {fallback_path}")
        return fallback_path

    fallback_path.parent.mkdir(parents=True, exist_ok=True)
    logging.info(f"⚠️ {description} not found or invalid. Downloading to {fallback_path}...")

    result = os.system(f"dx download {file_id} -o {fallback_path} --overwrite")
    if result != 0 or not fallback_path.exists():
        raise FileNotFoundError(f"❌ Failed to download {description} ({file_id})")

    logging.info(f"✅ Downloaded {description} to {fallback_path}")
    return fallback_path

# --- HELPER TO RESOLVE FILE PATHS FROM CONFIG ---
def resolve_path(config, file_info):
    base_key = file_info["BASE"]
    parts = base_key.split(".")
    base_path = config["BASE_PATHS"]
    for part in parts:
        base_path = base_path[part]
    return Path(config["PROJECT_DIR_PATH"]) / base_path / file_info["FILENAME"]

def get_file(file_info, config):
    file_path = resolve_path(config, file_info)
    return load_or_download_file(file_path, file_info["ID"], file_info["FILENAME"])

# --- EXTRACT FIELDS USING DX ---
def extract_fields(dataset_id, field_list_path, output_file, sql_only=False):
    try:
        df = pd.read_csv(field_list_path)
        if not {'entity', 'name'}.issubset(df.columns):
            raise ValueError("Input file must contain 'entity' and 'name' columns.")

        field_names = ','.join(
            f"{str(row['entity']).strip()}.{str(row['name']).strip()}" 
            for _, row in df.iterrows()
        )

        if sql_only:
            sql_file = "extracted_query.sql"
            cmd = [
                "dx", "extract_dataset",
                dataset_id,
                "--fields", field_names,
                "--output", sql_file,
                "--sql"
            ]
            subprocess.check_call(cmd)
            logging.info(f"✅ SQL query generated and saved to {sql_file}")

            Path(output_file).parent.mkdir(parents=True, exist_ok=True)
            shutil.move(sql_file, output_file)
            logging.info(f"✅ SQL file moved to {output_file}")
            return  # ✅ Exit after SQL-only path

        # Standard data extraction
        temp_output = "temp_extracted_data.csv"
        cmd_extract = [
            "dx", "extract_dataset",
            dataset_id,
            "--fields", field_names,
            "--delimiter", ",",
            "--output", temp_output,
        ]
        subprocess.check_call(cmd_extract)

        pd.read_csv(temp_output).to_csv(output_file, index=False)
        os.remove(temp_output)
        logging.info(f"✅ Dataset extracted and saved to {output_file}")

    except Exception as e:
        logging.error(f"❌ Failed to extract dataset: {e}")
        raise

# --- MAIN EXECUTION LOGIC ---
def run_extraction(output_path: Path, phenotype_key="PILOT_PHENOTYPES", dataset_id_override=None, sql_only=False, cohort_key="TEST_COHORT"):
    config_path = load_or_download_file(HELPERS_DIR / CONFIG_FILENAME, CONFIG_FILE_ID, "Config file", validate_json=True)
    with open(config_path, "r") as f:
        config = json.load(f)

    pheno_info = config["FILES"]["PHENOTYPE_FILES"][phenotype_key]
    pheno_path = resolve_path(config, pheno_info)
    pheno_list_file = resolve_path(config, config["FILES"]["PHENOTYPE_FILES"][phenotype_key])
    if not pheno_list_file.exists():
        pheno_list_file = load_or_download_file(pheno_list_file, pheno_info["ID"], pheno_info["FILENAME"])
    else:
        logging.info(f"✅ Using existing phenotype list at {pheno_list_file}")

    if dataset_id_override:
        dataset_id = dataset_id_override
    else:
        try:
            dataset_id = config["COHORTS"][cohort_key]
        except KeyError:
            available = ", ".join(config["COHORTS"].keys())
            raise KeyError(f"❌ Cohort key '{cohort_key}' not found. Available keys: {available}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    if sql_only and not str(output_path).endswith(".sql"):
        logging.warning("⚠️ Output file ends in .csv but SQL mode is enabled. Your output file may be invalid.")

    extract_fields(
        dataset_id, 
        pheno_list_file, 
        str(output_path), 
        sql_only=sql_only
    )
    logging.info(f"✅ Output saved to {output_path.resolve()}")

# --- PUBLIC ENTRYPOINT FOR NOTEBOOK OR IMPORT ---
def main(
    output_file="outputs/pilot_phenotypes_raw_values.csv",
    phenotype_key="PILOT_PHENOTYPES",
    cohort_key="TEST_COHORT", 
    dataset_id=None, 
    sql_only=False
):
    run_extraction(
        Path(output_file), 
        phenotype_key, 
        dataset_id_override=dataset_id, 
        sql_only=sql_only, 
        cohort_key=cohort_key
    )

# --- CLI ENTRY POINT ---
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(
        description="Extract phenotype values or SQL from DNAnexus using config-defined field list."
    )
    parser.add_argument("--phenotype", type=str, default="PILOT_PHENOTYPES")
    parser.add_argument("--output", type=str, default="outputs/raw/pilot_phenotypes_raw_values.csv")
    parser.add_argument("--cohort", type=str, default="TEST_COHORT")
    parser.add_argument("--dataset", type=str, default=None)
    parser.add_argument("--sql-only", action="store_true")
    args = parser.parse_args()

    main(
        output_file=args.output,
        phenotype_key=args.phenotype,
        cohort_key=args.cohort,
        dataset_id=args.dataset,
        sql_only=args.sql_only
    )