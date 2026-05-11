import pandas as pd
import os
import re

# 1. PATH CONFIGURATION
PATH_READINGS = r"D:\%PRACA_MAGISTERSKA\data\interim\new_readings_to_import.csv"
PATH_META_IN = r"D:\%PRACA_MAGISTERSKA\data\interim\sensors_metadata.csv"
PATH_META_OUT = r"D:\%PRACA_MAGISTERSKA\data\interim\sensors_metadata_v2.csv"

def get_base_id(sensor_id):
    """Extracts the core name of the sensor to search for similar units"""
    # Remove suffixes: _R, _B, _BX, _BY, _BZ, _T, _M1, _M2
    clean = re.sub(r'(_?[R|B|BX|BY|BZ|T|M1|M2])$', '', str(sensor_id))
    # Remove any trailing letter (e.g., CM0010_01B -> CM0010_01)
    return re.sub(r'[A-Z]$', '', clean).strip('_')

# 2. SYNCHRONIZATION FUNCTION
def perform_sync():
    print("Starting strict metadata synchronization...")
    
    # Load datasets
    df_readings = pd.read_csv(PATH_READINGS, usecols=['sensor_id'])
    df_meta = pd.read_csv(PATH_META_IN)
    
    # Identify unique sensors from readings and existing metadata
    all_readings_ids = df_readings['sensor_id'].unique()
    existing_meta_ids = set(df_meta['sensor_id'].unique())
    
    new_rows = []
    ignored_count = 0
    
    for sid in all_readings_ids:
        # Skip if metadata already exists for this ID
        if sid in existing_meta_ids:
            continue
            
        # Attempt to recover coordinates using Fuzzy Matching on the Base ID
        base = get_base_id(sid)
        match = df_meta[df_meta['sensor_id'].str.contains(base, na=False)]
        
        if not match.empty:
            # RECOVERY: Copy coordinates from the identified "parent" sensor
            ref = match.iloc[0]
            new_rows.append({
                'sensor_id': sid,
                'latitude': ref['latitude'],
                'longitude': ref['longitude'],
                'altitude': ref['altitude'],
                'description': f"Automatic match based on {ref['sensor_id']}"
            })
        else:
            # EXCLUSION: If no location data can be found, the sensor is skipped
            ignored_count += 1
            
    # Combine original metadata with newly recovered records
    df_final = pd.concat([df_meta, pd.DataFrame(new_rows)], ignore_index=True)
    df_final.to_csv(PATH_META_OUT, index=False)
    
    print("-" * 30)
    print("SYNCHRONIZATION COMPLETE")
    print(f"Total sensors in new metadata: {len(df_final)}")
    print(f"Sensors recovered via matching: {len(new_rows)}")
    print(f"Sensors permanently excluded (no location): {ignored_count}")
    print(f"Result file: {PATH_META_OUT}")

# 3. EXECUTION
if __name__ == "__main__":
    perform_sync()