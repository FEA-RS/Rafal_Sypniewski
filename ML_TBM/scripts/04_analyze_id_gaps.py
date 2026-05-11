import pandas as pd
import os
import re

# 1. PATH CONFIGURATION
PATH_READINGS = r"D:\%PRACA_MAGISTERSKA\data\interim\new_readings_to_import.csv"
PATH_META = r"D:\%PRACA_MAGISTERSKA\data\interim\sensors_metadata.csv"
PATH_OUTPUT_REPORT = r"D:\%PRACA_MAGISTERSKA\results\reports\raport_naprawczy_id.txt"

def get_base_id(sensor_id):
    """Extracts the core ID by removing measurement-specific suffixes (R, B, BX, etc.)"""
    # Remove suffixes: _R, _B, _BX, _BY, _BZ, _T, _M1, _M2 and coordinate indicators
    clean = re.sub(r'(_?[R|B|BX|BY|BZ|T|M1|M2])$', '', str(sensor_id))
    # Remove trailing letters if they remain (e.g., CM0010_01B -> CM0010_01)
    clean = re.sub(r'[A-Z]$', '', clean)
    return clean.strip('_')

# 2. ANALYSIS FUNCTION
def analyze_repair_potential():
    if not os.path.exists(PATH_READINGS) or not os.path.exists(PATH_META):
        print("ERROR: Source files missing in the interim folder.")
        return

    # Load datasets
    df_readings = pd.read_csv(PATH_READINGS, usecols=['sensor_id', 'measurement_desc'])
    df_meta = pd.read_csv(PATH_META, usecols=['sensor_id'])

    readings_ids = set(df_readings['sensor_id'].unique())
    meta_ids = set(df_meta['sensor_id'].unique())

    # Identify IDs present in readings but missing from metadata
    missing_ids = readings_ids - meta_ids
    
    recoverable = []
    unrecoverable = []

    for mid in missing_ids:
        base = get_base_id(mid)
        # Check if metadata contains any ID matching this base core
        matches = [m for m in meta_ids if base in m]
        
        count = len(df_readings[df_readings['sensor_id'] == mid])
        
        if matches:
            recoverable.append({
                'id': mid,
                'base_found': matches[0],
                'rows': count
            })
        else:
            unrecoverable.append({
                'id': mid,
                'rows': count
            })

    # 3. REPORT GENERATION
    total_rows = len(df_readings)
    rows_to_recover = sum(item['rows'] for item in recoverable)
    rows_lost = sum(item['rows'] for item in unrecoverable)

    with open(PATH_OUTPUT_REPORT, 'w', encoding='utf-8') as f:
        f.write("DETAILED INTEGRITY AND RECOVERY POTENTIAL REPORT\n")
        f.write("="*60 + "\n")
        f.write(f"Total records in file: {total_rows}\n")
        f.write(f"Valid records (already in metadata): {total_rows - rows_to_recover - rows_lost}\n")
        f.write(f"Records RECOVERABLE: {rows_to_recover} ({ (rows_to_recover/total_rows)*100 :.2f}%)\n")
        f.write(f"Records DEFINITIVELY lost: {rows_lost} ({ (rows_lost/total_rows)*100 :.2f}%)\n")
        f.write("-" * 60 + "\n\n")

        f.write("1. LIST FOR AUTOMATIC RECOVERY (Base ID exists in metadata):\n")
        f.write(f"{'SENSOR ID':<20} | {'BASE FOUND':<20} | {'ROW COUNT':<15}\n")
        f.write("-" * 60 + "\n")
        for item in sorted(recoverable, key=lambda x: x['rows'], reverse=True):
            f.write(f"{item['id']:<20} | {item['base_found']:<20} | {item['rows']:<15}\n")

        f.write("\n2. LIST TO BE SKIPPED (No reference point in metadata):\n")
        f.write(f"{'SENSOR ID':<20} | {'ROW COUNT':<15}\n")
        f.write("-" * 40 + "\n")
        for item in sorted(unrecoverable, key=lambda x: x['rows'], reverse=True):
            f.write(f"{item['id']:<20} | {item['rows']:<15}\n")

    print(f"Analysis complete. Report: {PATH_OUTPUT_REPORT}")

# EXECUTION
if __name__ == "__main__":
    analyze_repair_potential()