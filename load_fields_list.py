import pandas as pd
import json
import sys
import os
from pathlib import Path

# --- CONFIG CONSTANTS ---
CONFIG_FILENAME = "config.json"
HELPERS_DIR = Path("/mnt/project/helpers")
CONFIG_FILE_ID = "file-J11J1892JqxXpGPBbQy6pjJj"

# --- GENERIC FILE LOADER ---
def load_or_download_file(file_path: Path, file_id: str, description: str = "", config_mode: bool = False):
    def is_valid_json(path: Path):
        try:
            with open(path, "r") as f:
                json.load(f)
            return True
        except Exception:
            return False

    if file_path.exists() and is_valid_json(file_path):
        return file_path

    if config_mode:
        # Use fallback directly in current directory
        fallback_path = Path("helpers") / file_path.name
    else:
        # Use project-relative fallback
        project_root = Path("/mnt/project").resolve()
        relative_path = file_path.relative_to(project_root)
        fallback_path = Path(".") / relative_path

    fallback_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"⚠️ {description} not found or invalid at {file_path}, downloading to local path: {fallback_path}")
    if fallback_path.exists():
        response = input(f"⚠️ Local file '{fallback_path}' exists. Overwrite? [y/N]: ").strip().lower()
        if response != 'y':
            print("⏭️ Skipping download. Using existing local file.")
            return fallback_path

    result = os.system(f"dx download {file_id} -o {fallback_path} --overwrite")
    if result != 0 or not fallback_path.exists():
        raise FileNotFoundError(f"❌ Failed to download {description} ({file_id})")

    return fallback_path

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

def float_to_int_if_possible(val):
    try:
        float_val = float(val)
        int_val = int(float_val)
        return int_val if float_val == int_val else float_val
    except (ValueError, TypeError):
        return val

def strip_strings(df):
    return df.apply(lambda col: col.str.strip() if col.dtype == "object" else col)

# --- MAIN FUNCTION ---
def main(input_file: str, output_file: str):
    """
    Main entry point for processing a phenotype list into a merged metadata file.

    Args:
        input_file (str): Path to the input phenotype CSV file, or "-" to use the file specified in config["FILES"]["PHENOTYPE_FILES"]["PILOT_PHENOTYPES"].
            - The input file should contain at minimum the columns: 'phenotype', 'coding_name', 'entity', and 'name'.
        output_file (str): Path to the output CSV file where the processed phenotype metadata will be saved.

    Process:
        1. Loads the global project config file (downloads if needed).
        2. Loads the `utils.py` module specified in config.
        3. Resolves file paths to:
            - The phenotype list (from input_file or config)
            - The codings file
            - The data dictionary file
        4. Loads and strips whitespace from all input FILES.
        5. Merges the phenotype list with the codings and data dictionary FILES to fill in metadata fields.
        6. Ensures the number of rows remains unchanged throughout.
        7. Writes the final processed DataFrame to the specified output path.

    Returns:
        None — saves results to output_file and prints status to stdout.
    """
    output_path = Path(output_file)
    try:
        config_path = load_or_download_file(HELPERS_DIR / CONFIG_FILENAME, CONFIG_FILE_ID, "Config file", config_mode=True)
        with open(config_path, "r") as f:
            config = json.load(f)
    except Exception as e:
        raise RuntimeError(f"❌ Failed to load config file from {config_path}: {e}")

    utils_info = config["FILES"]["UTILS"]
    utils_path = get_file(utils_info, config)
    sys.path.insert(0, str(resolve_path(config, utils_info).parent.resolve()))
    import utils

    if input_file == "-":
        pheno_info = config["FILES"]["PHENOTYPE_FILES"]["PILOT_PHENOTYPES"]
        base_parts = pheno_info["BASE"].split(".")
        base_path = config["BASE_PATHS"]
        for part in base_parts:
            base_path = base_path[part]
        input_path = Path(config["PROJECT_DIR_PATH"]) / base_path / pheno_info["FILENAME"]
        input_file = load_or_download_file(input_path, pheno_info["ID"], pheno_info["FILENAME"])

    # Get other required FILES
    coding_file = get_file(config["FILES"]["CODINGS"], config)
    data_dict_file = get_file(config["FILES"]["DATA_DICT"], config)

    # Load data
    raw_pheno_df = utils.load_file(input_file)
    coding_df = utils.load_file(coding_file)
    data_dict_df = utils.load_file(data_dict_file)

    # Clean
    raw_pheno_df = strip_strings(raw_pheno_df)
    coding_df = strip_strings(coding_df)
    data_dict_df = strip_strings(data_dict_df)

    # Merge
    intermed_df = pd.merge(
        raw_pheno_df,
        coding_df,
        how="left",
        left_on=["coding_name", "phenotype"],
        right_on=["coding_name", "meaning"],
        suffixes=('', '_from_coding')
    )
    intermed_df["code"] = intermed_df["code"].fillna(intermed_df["code_from_coding"])
    intermed_df["code"] = intermed_df["code"].apply(float_to_int_if_possible)
    intermed_df.drop(columns=[c for c in ["code_from_coding", "meaning", "concept", "display_order"] if c in intermed_df.columns], inplace=True)

    processed_df = pd.merge(
        intermed_df,
        data_dict_df,
        how="left",
        on=["name", "entity"],
        suffixes=('', '_from_dict')
    )
    for col in processed_df.columns:
        if col.endswith('_from_dict'):
            processed_df.rename(columns={col: col.replace('_from_dict', '')}, inplace=True)

    assert len(processed_df) == len(raw_pheno_df), (
        f"Row count changed during merge! Original: {len(raw_pheno_df)}, After merge: {len(processed_df)}"
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    processed_df.to_csv(output_path, index=False)
    print(f"✅ Output saved to {output_path.resolve()}")

# --- CLI WRAPPER ---
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Process phenotype list and save output.")
    parser.add_argument("input_file", type=str, help="Input file or '-' to use default from config")
    parser.add_argument("output_file", type=str, help="Output CSV file path")
    args = parser.parse_args()
    main(args.input_file, args.output_file)