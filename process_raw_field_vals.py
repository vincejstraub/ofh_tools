import pandas as pd
import numpy as np
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO)

def load_input(input_data):
    """Load input data from file path or return a copy of the DataFrame."""
    if isinstance(input_data, (str, Path)):
        input_path = Path(input_data)
        logging.info(f"📅 Reading input file: {input_path}")
        try:
            return pd.read_csv(input_path)
        except Exception as e:
            logging.error(f"❌ Failed to read input file: {e}")
            raise
    elif isinstance(input_data, pd.DataFrame):
        logging.info(f"📊 Using input DataFrame with {len(input_data)} rows")
        return input_data.copy()
    else:
        raise ValueError("input_data must be a file path or a pandas DataFrame")

def derive_age_at_recruiment(df):
    """
    Derive age at recruiment from registration and birth date columns.
    Only runs if required columns are present.
    """
    required_cols = {
        'participant.registration_year', 'participant.registration_month',
        'participant.birth_year', 'participant.birth_month'
    }
    if not required_cols.issubset(df.columns):
        logging.warning("⚠️ Skipping age derivation: required columns not found.")
        return df

    logging.info("🧲 Deriving age from birth and registration dates")
    df['registration_date'] = pd.to_datetime(dict(
        year=df['participant.registration_year'],
        month=df['participant.registration_month'],
        day=1
    ), errors='coerce')
    df['birth_date'] = pd.to_datetime(dict(
        year=df['participant.birth_year'],
        month=df['participant.birth_month'],
        day=1
    ), errors='coerce')
    df['age_at_recruitment'] = (df['registration_date'] - df['birth_date']).dt.days / 365.25
    return df

def apply_exclusions(df):
    """
    Apply standard exclusion filters to the DataFrame.
    Exclusions include:
    - birth_year == -999
    - sex in [3, -3] or missing
    - ethnicity in [19, -3]
    - income in [-1, -3] or missing
    - age < 18 (only if 'age' column exists)
    
    Only applies filters if columns are present.
    """
    logging.info("❌ Applying exclusion filters")
    conditions = []
    if 'participant.birth_year' in df.columns:
        conditions.append(df['participant.birth_year'] != -999)
    if 'participant.demog_sex_2_1' in df.columns:
        conditions.append(~df['participant.demog_sex_2_1'].isin([3, -3]))
        conditions.append(df['participant.demog_sex_2_1'].notna())
    if 'participant.demog_ethnicity_1_1' in df.columns:
        conditions.append(~df['participant.demog_ethnicity_1_1'].isin([19, -3]))
    if 'questionnaire.housing_income_1_1' in df.columns:
        conditions.append(~df['questionnaire.housing_income_1_1'].isin([-1, -3]))
        conditions.append(df['questionnaire.housing_income_1_1'].notna())
    if 'age' in df.columns:
        conditions.append(df['age'] >= 18)

    if conditions:
        from functools import reduce
        df = df[reduce(lambda x, y: x & y, conditions)]
    else:
        logging.warning("⚠️ No applicable exclusions applied.")

    return df

def process_raw_data(input_data, output_file=None):
    """
    Clean and process a raw phenotype dataset.

    Steps:
    1. Loads input data (CSV or DataFrame).
    2. Optionally derives age at recruitment from birth and registration dates if columns exist.
    3. Applies the following exclusion filters if corresponding columns are present:
       - Exclude participants with birth_year == -999
       - Exclude participants with sex values 3 (intersex) or -3 (prefer not to answer)
       - Exclude participants with ethnicity codes 19 or -3
       - Exclude participants with housing_income values -1 (don't know), -3 (prefer not to answer), or missing
       - Exclude participants under 18 (requires age derivation)
    4. Optionally saves output to a file if specified.

    Args:
        input_data (str, Path, or pd.DataFrame): Input CSV file path or raw DataFrame.
        output_file (str or Path, optional): If provided, saves cleaned data to this file.

    Returns:
        pd.DataFrame: Cleaned and processed phenotype DataFrame.
    """
    df = load_input(input_data)
    df = derive_age(df)
    df = apply_exclusions(df)

    if output_file:
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(output_path, index=False)
        logging.info(f"✅ Saved cleaned data to {output_path}")

    return df


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Clean and process phenotype data.")
    parser.add_argument("input_file", type=str, help="Path to input CSV file")
    parser.add_argument("output_file", type=str, help="Path to output CSV file")
    args = parser.parse_args()

    process_raw_data(args.input_file, args.output_file)
    