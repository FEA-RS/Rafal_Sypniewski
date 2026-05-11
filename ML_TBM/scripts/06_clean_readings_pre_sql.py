import pandas as pd
import os

# 1. PATH CONFIGURATION
PATH_READINGS = r"D:\%PRACA_MAGISTERSKA\data\interim\new_readings_to_import.csv"
PATH_META = r"D:\%PRACA_MAGISTERSKA\data\interim\sensors_metadata_v2.csv"
PATH_CLEANED_OUT = r"D:\%PRACA_MAGISTERSKA\data\interim\readings_FOR_SQL_FINAL.csv"

def clean_readings_for_sql():
    print("Starting data filtering...")
    
    # 1. Load valid IDs from metadata to serve as a whitelist
    df_meta = pd.read_csv(PATH_META, usecols=['sensor_id'])
    valid_ids = set(df_meta['sensor_id'].unique())
    
    # 2. Process readings in chunks to optimize RAM usage
    chunk_size = 500000
    first_chunk = True
    total_cleaned = 0
    total_original = 0
    
    for chunk in pd.read_csv(PATH_READINGS, chunksize=chunk_size):
        total_original += len(chunk)
        
        # Filter: keep only rows where sensor_id exists in metadata
        cleaned_chunk = chunk[chunk['sensor_id'].isin(valid_ids)]
        total_cleaned += len(cleaned_chunk)
        
        # Save to a new file (write mode for the first chunk, append mode for subsequent chunks)
        if first_chunk:
            cleaned_chunk.to_csv(PATH_CLEANED_OUT, index=False, mode='w')
            first_chunk = False
        else:
            cleaned_chunk.to_csv(PATH_CLEANED_OUT, index=False, mode='a', header=False)
            
        print(f"Processed: {total_original} rows...")

    print("-" * 30)
    print(f"SUCCESS! File cleaned.")
    print(f"Original row count: {total_original}")
    print(f"Rows ready for SQL: {total_cleaned}")
    print(f"Removed 'garbage' records: {total_original - total_cleaned}")
    print(f"Output file: {PATH_CLEANED_OUT}")

# EXECUTION
if __name__ == "__main__":
    clean_readings_for_sql()