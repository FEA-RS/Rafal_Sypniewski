import pandas as pd
import os

PATH_RAW_COORDS = r"D:\%PRACA_MAGISTERSKA\data\raw\tbm_pozycjonowanie\tunnel_progress_with_coords.xlsx"
PATH_INTERIM_COORDS = r"D:\%PRACA_MAGISTERSKA\data\interim\ring_tbm_coords.csv"

def przetworz_coords_ring():
    df = pd.read_excel(PATH_RAW_COORDS, engine='openpyxl')
    
    # Upewniamy się, że data jest czytelna
    df['date'] = pd.to_datetime(df['date'], dayfirst=True, errors='coerce')
    
    if 'ring' not in df.columns:
        df['ring'] = range(1, len(df) + 1)

    df['lat_center'] = (df['lat1'] + df['lat2']) / 2
    df['lon_center'] = (df['lon1'] + df['lon2']) / 2

    df[['ring', 'lat_center', 'lon_center', 'date']].to_csv(PATH_INTERIM_COORDS, index=False)
    print(f"Zapisano koordynaty dla {len(df)} ringów.")

if __name__ == "__main__":
    przetworz_coords_ring()