import pandas as pd
import os

# 1. PATH CONFIGURATION
PATH_RAW_COORDS = r"D:\%PRACA_MAGISTERSKA\data\raw\tbm_pozycjonowanie\tunnel_progress_with_coords.xlsx"
PATH_INTERIM_COORDS = r"D:\%PRACA_MAGISTERSKA\data\interim\ring_tbm_coords.csv"

# 2. PROCESSING FUNCTION
def process_ring_coordinates():
    """Processes TBM positioning data and calculates ring center coordinates"""
    
    # Load raw coordinate data from Excel
    df = pd.read_excel(PATH_RAW_COORDS, engine='openpyxl')
    
    # Ensure the date format is standardized and readable
    df['date'] = pd.to_datetime(df['date'], dayfirst=True, errors='coerce')
    
    # Generate ring numbers if the column is missing based on row count
    if 'ring' not in df.columns:
        df['ring'] = range(1, len(df) + 1)

    # Calculate center point coordinates for each ring
    df['lat_center'] = (df['lat1'] + df['lat2']) / 2
    df['lon_center'] = (df['lon1'] + df['lon2']) / 2

    # Select relevant columns and export to interim CSV
    df[['ring', 'lat_center', 'lon_center', 'date']].to_csv(PATH_INTERIM_COORDS, index=False)
    print(f"Success! Saved coordinates for {len(df)} rings.")

# EXECUTION
if __name__ == "__main__":
    process_ring_coordinates()