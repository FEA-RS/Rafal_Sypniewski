import pandas as pd
from sqlalchemy import create_engine
import os
import re

# --- KONFIGURACJA ---
DB_USER = "postgres"
DB_PASS = "imgpan"
DB_HOST = "localhost"
DB_PORT = "5432"
DB_NAME = "magisterka_tbm"

PATH_SAVE = r"D:\%PRACA_MAGISTERSKA\data\interim"

def parse_soil_categories(df):
    """
    Parsuje tekstową kolumnę soil_category (np. '5% VIC 91% VIIA') 
    na osobne kolumny numeryczne (0.05, 0.91).
    """
    print("Parsowanie geologii na cechy numeryczne (Input dla ML)...")
    parsed_list = []
    
    for val in df['soil_category']:
        row_dict = {}
        if pd.notnull(val):
            # Wyciąga procent i nazwę warstwy
            matches = re.findall(r'(\d+)%\s+([A-Z0-9]+)', str(val))
            for pct, name in matches:
                row_dict[f"soil_{name}"] = int(pct) / 100.0
        parsed_list.append(row_dict)
    
    df_soil = pd.DataFrame(parsed_list).fillna(0)
    df = pd.concat([df.reset_index(drop=True), df_soil.reset_index(drop=True)], axis=1)
    return df.drop(columns=['soil_category'])

def extract_data_to_parquet():
    # Połączenie do bazy
    connection_string = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    engine = create_engine(connection_string)
    
    print("Ekstrakcja danych zgodnie z poprawioną strukturą...")

    # SQL - TYLKO konkretne parametry, bez zbędnych sum
    tbm_query = """
    SELECT 
        ring, 
        timestamp,
        latitude, 
        longitude,
        
        -- EPB: Poziom i Stabilność
        epb_avg, 
        (epb_max - epb_min) as epb_range,
        
        -- Napęd: Praca i Szarpanie
        torque_avg, 
        (torque_max - torque_min) as torque_range,
        thrust_avg,
        (thrust_max - thrust_min) as thrust_range,
        
        -- Iniekcja: Kluczowy parametr sterowalny
        (grout_injected / NULLIF(grout_expected, 0)) as grout_ratio,
        
        -- Kondycjonowanie: Piana i Bentonit (poprawione nazwy wg Twojej tabeli)
        (COALESCE(foam_poly_vol, 0) + COALESCE(foam_surf_vol, 0) + COALESCE(foam_water_vol, 0)) as total_foam_vol,
        cond_soil_vol_v6 as total_bentonite_vol,
        
        -- Geologia do późniejszego parsowania
        soil_category
        
    FROM tbm_telemetry
    ORDER BY ring ASC;
    """
    
    # 1. Pobranie i obróbka TBM
    df_tbm = pd.read_sql(tbm_query, engine)
    df_tbm = parse_soil_categories(df_tbm)

    # 2. Pobranie Monitoringu (Target)
    sensors_query = """
    SELECT 
        r.timestamp,
        r.sensor_id,
        r.settlement_value,
        m.latitude,
        m.longitude
    FROM monitoring_readings r
    JOIN sensors_metadata m ON r.sensor_id = m.sensor_id
    WHERE r.reading_type = 'Z'
    ORDER BY r.timestamp ASC;
    """
    
    print("Pobieram monitoring (Z)...")
    df_sensors = pd.read_sql(sensors_query, engine)

    # 3. Zapis do plików
    os.makedirs(PATH_SAVE, exist_ok=True)
    tbm_file = os.path.join(PATH_SAVE, "tbm_features_ring.parquet")
    sensors_file = os.path.join(PATH_SAVE, "sensors_readings_spatial.parquet")
    
    df_tbm.to_parquet(tbm_file, index=False)
    df_sensors.to_parquet(sensors_file, index=False)

    print("-" * 30)
    print("GOTOWE!")
    print(f"Ringi: {len(df_tbm)}, Kolumny geologii: {[c for c in df_tbm.columns if c.startswith('soil_')]}")

if __name__ == "__main__":
    extract_data_to_parquet()