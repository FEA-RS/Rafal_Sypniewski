import os
import pandas as pd
from datetime import datetime
import re

# 1. CONFIGURATION
INPUT_FOLDER = r"D:\%PRACA_MAGISTERSKA\data\raw\odczyty_czujnikow"
MASTER_FILE = r"D:\%PRACA_MAGISTERSKA\data\interim\master_readings.csv"
IMPORT_FILE = r"D:\%PRACA_MAGISTERSKA\data\interim\new_readings_to_import.csv"
REPORT_PATH = r"D:\%PRACA_MAGISTERSKA\results\reports\ETL_raport_odczyty.txt"

SQL_COLUMNS = ['timestamp', 'sensor_id', 'settlement_value', 'reading_type', 'measurement_desc']

DESCRIPTION_MAP = {
    'R': 'Reading on benchmark',
    'BZ': 'Vertical displacement (Z-axis)',
    'BX': 'Horizontal displacement (X-axis)',
    'BY': 'Horizontal displacement (Y-axis)'
}

def clean_sensor_id(s_name):
    """Clean Sensor ID to match database format requirements"""
    s_name = s_name.strip().upper()
    
    # 1. If ending with BX, BY, BZ -> trim the last coordinate letter (keep 'B')
    s_name = re.sub(r'([XYZ])$', '', s_name)
    
    # 2. Normalization: Remove internal tags like _A_ or _D_
    s_name = s_name.replace('_A_', '_').replace('_D_', '_')
    
    return s_name

# 2. DATA PROCESSING FUNCTION
def prepare_readings():
    print("Starting data cleaning and processing...")
    new_data_list = []
    processed_sheets_count = 0

    # Iterate through Excel files in the raw data directory
    for file in os.listdir(INPUT_FOLDER):
        if file.endswith(".xlsx") and not file.startswith("~$"):
            path = os.path.join(INPUT_FOLDER, file)
            filename_lower = file.lower()
            
            # Determine measurement type based on filename keywords (using original Polish names)
            measurement_type = "Z" if "osi z" in filename_lower else "XY" if "osiach x i y" in filename_lower else "UNKNOWN"
            
            try:
                excel_file = pd.ExcelFile(path)
                for sheet_name in excel_file.sheet_names:
                    orig_name = str(sheet_name).strip()
                    
                    # Filter sheets based on specific measurement suffixes (R, BZ, BX, BY)
                    measurement_desc = None
                    for suffix, description in DESCRIPTION_MAP.items():
                        if orig_name.endswith(suffix):
                            measurement_desc = description
                            break
                    
                    if not measurement_desc:
                        continue
                    
                    processed_sheets_count += 1
                    df = pd.read_excel(path, sheet_name=sheet_name, usecols=[0, 1], 
                                     names=['timestamp', 'settlement_value'], header=0)
                    
                    # Apply cleaning and metadata
                    df['sensor_id'] = clean_sensor_id(orig_name)
                    df['reading_type'] = measurement_type
                    df['measurement_desc'] = measurement_desc 
                    df['timestamp'] = pd.to_datetime(df['timestamp'], dayfirst=True, errors='coerce')
                    
                    # Remove invalid records
                    df.dropna(subset=['timestamp', 'settlement_value'], inplace=True)
                    
                    new_data_list.append(df[SQL_COLUMNS])
                    
            except Exception as e:
                print(f"Error processing file {file}: {e}")

    if not new_data_list:
        print("No valid data found.")
        return

    # Merge all data and remove duplicates
    df_final = pd.concat(new_data_list, ignore_index=True)
    df_final.drop_duplicates(subset=['sensor_id', 'timestamp', 'measurement_desc'], inplace=True)
    
    # Sort and export results to master and import-ready files
    df_final.sort_values(by=['sensor_id', 'timestamp'], inplace=True)
    final_master_path = MASTER_FILE
    df_final.to_csv(final_master_path, index=False)
    df_final.to_csv(IMPORT_FILE, index=False)
    
    print(f"Success! Processed {processed_sheets_count} sheets. Generated {len(df_final)} records.")

# EXECUTION
if __name__ == "__main__":
    prepare_readings()