import pandas as pd
import numpy as np
import os

# --- KONFIGURACJA ---
PATH_TBM = r"D:\%PRACA_MAGISTERSKA\data\interim\tbm_features_ring.parquet"
PATH_SENSORS = r"D:\%PRACA_MAGISTERSKA\data\interim\sensors_interpolated.parquet"
PATH_AUDIT_CSV = r"D:\%PRACA_MAGISTERSKA\results\reports\ring_audit_detailed.csv"
PATH_AUDIT_SUMMARY = r"D:\%PRACA_MAGISTERSKA\results\reports\ring_audit_summary.txt"

# Okno identyczne jak w skrypcie 12 (do liczenia objętości)
SHIELD_DIAMETER = 13.0
WINDOW_LONGITUDINAL = [-SHIELD_DIAMETER, 1.5*SHIELD_DIAMETER] # metry za i przed tarczą
WINDOW_TRANSVERSE = 5*SHIELD_DIAMETER/2         # metry w bok od osi


def audit_rings_window():
    print("Rozpoczynam audyt w oknie obliczeniowym (identycznym jak do liczenia niecki)...")
    
    # Wczytujemy i sortujemy
    df_tbm = pd.read_parquet(PATH_TBM).sort_values('ring')
    df_sensors = pd.read_parquet(PATH_SENSORS)
    
    df_tbm['date'] = pd.to_datetime(df_tbm['timestamp']).dt.date
    df_sensors['date'] = pd.to_datetime(df_sensors['date']).dt.date

    results = []
    bearing = 0 # Inicjalizacja kierunku

    for i in range(len(df_tbm)):
        ring = df_tbm.iloc[i]
        
        # Wyznaczanie kierunku tunelu (identycznie jak w skrypcie 12)
        if i < len(df_tbm) - 1:
            next_r = df_tbm.iloc[i+1]
            bearing = np.arctan2(next_r['longitude'] - ring['longitude'], next_r['latitude'] - ring['latitude'])
        
        day_sensors = df_sensors[df_sensors['date'] == ring['date']].copy()
        
        if day_sensors.empty:
            results.append({
                'ring': int(ring['ring']), 'date': ring['date'], 
                'pts_total': 0, 'pts_full': 0, 'pts_safe': 0, 'status': 'BRAK DANYCH'
            })
            continue

        # 1. Transformacja na metry
        d_lat = (day_sensors['latitude'] - ring['latitude']) * 111132
        d_lon = (day_sensors['longitude'] - ring['longitude']) * 71000
        
        # 2. Rotacja do układu tarczy (X=poprzeczny, Y=podłużny)
        dist_trans = d_lon * np.cos(bearing) - d_lat * np.sin(bearing)
        dist_long = d_lon * np.sin(bearing) + d_lat * np.cos(bearing)

        # 3. Filtracja okna
        in_window_mask = (dist_long >= WINDOW_LONGITUDINAL[0]) & \
                         (dist_long <= WINDOW_LONGITUDINAL[1]) & \
                         (np.abs(dist_trans) <= WINDOW_TRANSVERSE)
        
        pts_in_win = day_sensors[in_window_mask]
        
        count_full = pts_in_win['settlement_full'].notna().sum()
        count_safe = pts_in_win['settlement_safe'].notna().sum()
        
        results.append({
            'ring': int(ring['ring']),
            'date': ring['date'],
            'pts_total': len(pts_in_win),
            'pts_full': count_full,
            'pts_safe': count_safe,
            'status': 'OK' if count_safe >= 4 else 'ZA MAŁO PKT (SAFE)'
        })

    audit_df = pd.DataFrame(results).sort_values('ring')
    os.makedirs(os.path.dirname(PATH_AUDIT_CSV), exist_ok=True)
    audit_df.to_csv(PATH_AUDIT_CSV, index=False)
    
    # Statystyki
    rings_ok = len(audit_df[audit_df['pts_safe'] >= 4])
    
    with open(PATH_AUDIT_SUMMARY, 'w') as f:
        f.write("AUDYT OKNA OBLICZENIOWEGO\n")
        f.write(f"Zasieg podluzny: {WINDOW_LONGITUDINAL} m\n")
        f.write(f"Zasieg poprzeczny: +/- {WINDOW_TRANSVERSE} m\n")
        f.write("-" * 30 + "\n")
        f.write(f"Liczba ringów: {len(audit_df)}\n")
        f.write(f"Ringi z min. 4 pkt w SAFE: {rings_ok} ({rings_ok/len(audit_df):.1%})\n")
        f.write(f"Srednia liczba pkt/ring (SAFE): {audit_df['pts_safe'].mean():.1f}\n")

    print(f"Audyt okna zakonczony. Ringi gotowe: {rings_ok}/{len(audit_df)}")

if __name__ == "__main__":
    audit_rings_window()