import os
import dxdata
import json
import pandas as pd
import logging
from pathlib import Path

def connect_to_dataset():
    # Get project and record IDs
    project = os.getenv('DX_PROJECT_CONTEXT_ID')
    record = os.popen("dx find data --type Dataset --delimiter ',' | awk -F ',' '{print $5}'").read().rstrip()
    DATASET_ID = project + ":" + record

    # Load dataset
    dataset = dxdata.load_dataset(id=DATASET_ID)
    return dataset


def create_folder_if_not_exists(dx_folder_path):
    """
    Creates a folder in the specified DNAnexus project path if it doesn't exist already.
    
    Parameters:
    - dx_folder_path: Path where the folder should be created in the project.
    """
    command = f"dx mkdir -p {dx_folder_path}"  # Use `-p` to create parent folders as needed
    print(f"Running command: {command}")
    os.system(f"bash -c '{command}'")  # Run the command in bash
    

def upload_files(file_paths, dx_folder='results', subfolders=None):
    """
    Upload files to DNAnexus project using dx upload with optional subfolders.
    
    Parameters:
    - file_paths: List of file paths to upload.
    - dx_folder: Path in the project to upload to (default is 'results').
    - subfolders: Optional list of subfolders where each corresponding file 
        will be uploaded. If None, no subfolder is used.
    """
    # Ensure files exist and upload
    for i, file_path in enumerate(file_paths):
        if os.path.exists(file_path):
            # Create the subfolder path for each file if subfolders are provided
            subfolder = subfolders[i] if subfolders and i < len(subfolders) else None
            upload_folder = dx_folder
            if subfolder:
                # Create subfolder path and create the folder if it doesn't exist
                upload_folder = f"{dx_folder}/{subfolder}"
                create_folder_if_not_exists(upload_folder)

            # Build the dx upload command
            command = f"dx upload {file_path} --path {upload_folder}/"
            print(f"Running command: {command}")
            
            # Execute the dx upload command in bash
            os.system(f"bash -c '{command}'")  # Execute the dx upload command in bash
            print(f"Uploaded {file_path} to {upload_folder}")
        else:
            print(f"File not found: {file_path}")


# Load a file based on its file type (json, txt, csv, tsv, xlsx, etc.)
def load_file(file_path):
    try:
        file_extension = Path(file_path).suffix.lower()
        
        if file_extension == ".json":
            with open(file_path, 'r') as f:
                return json.load(f)
        
        elif file_extension == ".txt":
            with open(file_path, 'r') as f:
                return f.read().replace('\n', ',')  # If it's a list of fields (like in your case)
        
        elif file_extension == ".csv":
            return pd.read_csv(file_path)  # Load CSV into DataFrame
        
        elif file_extension == ".tsv":
            return pd.read_csv(file_path, delimiter='\t')  # Load TSV into DataFrame (tab-separated)
        
        elif file_extension == ".xlsx":
            return pd.read_excel(file_path)  # Load Excel into DataFrame
        
        else:
            logging.warning(f"Unsupported file type {file_extension} for {file_path}")
            return None

    except Exception as e:
        logging.error(f"Error loading file {file_path}: {e}")
        raise