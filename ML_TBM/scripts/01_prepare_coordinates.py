import os
import pandas as pd
from pyproj import Transformer
from datetime import datetime

# 1. PATH CONFIGURATION
INPUT_PATH = r"D:\%PRACA_MAGISTERSKA\data\raw\koordynaty\coordinate_copy.txt"
OUTPUT_PATH = r"D:\%PRACA_MAGISTERSKA\data\interim\sensors_metadata.csv"
REPORT_PATH = r"D:\%PRACA_MAGISTERSKA\results\reports\ETL_raport_koordynaty.txt"

# Initialize coordinate transformer (PUWG 2000 zone 6 -> WGS84)
transformer = Transformer.from_crs("EPSG:2177", "EPSG:4326", always_xy=False)

# 2. PROCESSING FUNCTION
def prepare_sensors():
    print("Starting coordinate reading and conversion...")
    
    # Load data from TXT file
    df = pd.read_csv(
        INPUT_PATH, 
        sep='\t', 
        header=None, 
        names=['sensor_id', 'X', 'Y', 'altitude'],
        usecols=[0, 1, 2, 3],       
        on_bad_lines='warn',        
        engine='python'             
    )
    
    # Remove duplicates: keep only the first entry per sensor_id
    df.drop_duplicates(subset=['sensor_id'], keep='first', inplace=True)
    
    initial_count = len(df)

    # Function to handle coordinate transformation
    def convert_row(row):
        if row['X'] == 0 and row['Y'] == 0:
            return pd.Series({
                'latitude': 0.0, 
                'longitude': 0.0,
                'description': 'VERIFICATION_REQUIRED_MISSING_COORDINATES'
            })
            
        lat, lon = transformer.transform(row['X'], row['Y'])
        return pd.Series({
            'latitude': round(lat, 6), 
            'longitude': round(lon, 6),
            'description': None
        })

    # Apply conversion
    df[['latitude', 'longitude', 'description']] = df.apply(convert_row, axis=1)
    
    # Calculate statistics for the report
    sensors_missing_coords = df[df['description'] == 'VERIFICATION_REQUIRED_MISSING_COORDINATES']
    error_count = len(sensors_missing_coords)
    
    # Export final table to CSV
    final_table = df[['sensor_id', 'latitude', 'longitude', 'altitude', 'description']]
    final_table.to_csv(OUTPUT_PATH, index=False)
    
    # 3. TEXT REPORT GENERATION
    with open(REPORT_PATH, 'w', encoding='utf-8') as file:
        file.write(f"--- COORDINATE PROCESSING REPORT ---\n")
        file.write(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        file.write(f"Sensors loaded from raw file: {initial_count}\n")
        file.write(f"Sensors saved to final file: {len(final_table)}\n")
        file.write(f"Sensors found with zero coordinates (0,0): {error_count}\n\n")
        
        if error_count > 0:
            file.write("List of sensors missing coordinates:\n")
            for sensor_id in sensors_missing_coords['sensor_id']:
                file.write(f" - {sensor_id}\n")
    
    print(f"Success! {len(final_table)} sensors converted.")
    print(f"ETL Report generated: {REPORT_PATH}")

# EXECUTION
if __name__ == "__main__":
    prepare_sensors()