import pandas as pd
import os

PATH_RAW_TBM = r"D:\%PRACA_MAGISTERSKA\data\raw\tbm_parametry\POL-SRD.xlsx"
PATH_INTERIM_PARAMS = r"D:\%PRACA_MAGISTERSKA\data\interim\ring_tbm_machine_params.csv"

def przetworz_parametry_ring():
    print("Przetwarzam parametry TBM z poprawką daty...")
    
    # Wczytujemy dane
    df = pd.read_excel(PATH_RAW_TBM, skiprows=4, header=None, engine='openpyxl')

    # Mapowanie kolumn
    column_mapping = {
        0: 'ring', 1: 'serial_number', 2: 'timestamp', 
        6: 'epb_avg', 7: 'epb_min', 8: 'epb_max',
        9: 'torque_avg', 10: 'torque_min', 11: 'torque_max', 
        12: 'thrust_avg', 13: 'thrust_min', 14: 'thrust_max', 
        15: 'soil_exc_density_avg', 16: 'soil_exc_volume', 17: 'soil_exc_weight', 
        18: 'grout_expected', 19: 'grout_injected', 
        20: 'foam_poly_vol', 21: 'foam_poly_weight',
        22: 'foam_surf_vol', 23: 'foam_surf_weight', 24: 'foam_water_vol', 
        25: 'bentonite_vol', 26: 'bentonite_weight', 27: 'cond_soil_vol_v6',
        28: 'cond_soil_sum_vol', 29: 'cond_soil_sum_weight', 30: 'muck_density',
        31: 'soil_category', 32: 'soil_description'
    }

    df = df[list(column_mapping.keys())].rename(columns=column_mapping)
    
    # --- POPRAWKA DATY ---
    # dayfirst=True obsłuży zarówno YYYY-MM-DD jak i DD/MM/YYYY poprawnie
    df['timestamp'] = pd.to_datetime(df['timestamp'], dayfirst=True, errors='coerce')
    
    # Czyścimy teksty
    for col in ['soil_category', 'soil_description']:
        df[col] = df[col].astype(str).replace(r'[\r\n]+', ' ', regex=True).str.strip()

    df.to_csv(PATH_INTERIM_PARAMS, index=False)
    print(f"Zapisano {len(df)} rekordów z poprawnymi datami.")

if __name__ == "__main__":
    przetworz_parametry_ring()