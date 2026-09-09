import pandas as pd
import numpy as np
import os
from scipy.interpolate import griddata

# --- KONFIGURACJA ---
SHIELD_DIAMETER = 13.0
ZONE_LONG = [-SHIELD_DIAMETER, SHIELD_DIAMETER] # [za, przed] 
ZONE_TRANS = 2*SHIELD_DIAMETER/2           # Szerokość korytarza 
TIME_WINDOW_DAYS = 0      # Ile dni po przejściu tarczy analizujemy osiadanie


PATH_TBM = r"D:\%PRACA_MAGISTERSKA\data\interim\tbm_features_ring.parquet"
PATH_SENSORS = r"D:\%PRACA_MAGISTERSKA\data\interim\sensors_interpolated.parquet"
OUTPUT_PATH = r"D:\%PRACA_MAGISTERSKA\data\interim\final_ml_data_griddata.csv"

def calculate_vloss_griddata():
    print("--- URUCHAMIAM ANALIZĘ PRZESTRZENNĄ (METODA GRIDDATA) ---")
    
    # Wczytanie danych
    if not os.path.exists(PATH_TBM) or not os.path.exists(PATH_SENSORS):
        print("BŁĄD: Nie znaleziono plików wejściowych!")
        return

    df_tbm = pd.read_parquet(PATH_TBM).sort_values('ring')
    df_sensors = pd.read_parquet(PATH_SENSORS)
    
    df_tbm['date'] = pd.to_datetime(df_tbm['timestamp']).dt.date
    df_sensors['date'] = pd.to_datetime(df_sensors['date']).dt.date
    
    # Pole powierzchni tarczy (m2)
    v_tunnel_nominal = (np.pi * SHIELD_DIAMETER**2) / 4
    final_results = []

    for i in range(len(df_tbm)):
        ring = df_tbm.iloc[i]
        ring_date = ring['date']
        end_date = ring_date + pd.Timedelta(days=TIME_WINDOW_DAYS)
        
        # 1. Obliczanie kierunku drążenia (Bearing)
        bearing = 0.0
        if i < len(df_tbm)-1:
            next_r = df_tbm.iloc[i+1]
            bearing = np.arctan2(next_r['longitude'] - ring['longitude'], 
                                 next_r['latitude'] - ring['latitude'])
        
        # 2. Wycinanie sensorów w oknie czasowym
        mask_time = (df_sensors['date'] >= ring_date) & (df_sensors['date'] <= end_date)
        window_sensors = df_sensors[mask_time].copy()
        
        if window_sensors.empty:
            continue

        # 3. Transformacja współrzędnych na układ lokalny tarczy (metry)
        # Przelicznik stopnie - metry 
        d_lat = (window_sensors['latitude'] - ring['latitude']) * 111132
        d_lon = (window_sensors['longitude'] - ring['longitude']) * 71000
        
        window_sensors['d_trans'] = d_lon * np.cos(bearing) - d_lat * np.sin(bearing)
        window_sensors['d_long'] = d_lon * np.sin(bearing) + d_lat * np.cos(bearing)

        # Wycięcie tylko punktów w pobliżu aktualnego ringu
        mask_space = (window_sensors['d_long'] >= ZONE_LONG[0]) & \
                     (window_sensors['d_long'] <= ZONE_LONG[1]) & \
                     (np.abs(window_sensors['d_trans']) <= ZONE_TRANS)
        
        pts = window_sensors[mask_space].dropna(subset=['settlement_full']).copy()
        #pts = window_sensors[mask_space].dropna(subset=['settlement_safe']).copy()
        
        # Wymagamy minimum 4 punktów, by stworzyć jakąkolwiek bryłę
        if len(pts) >= 4:
            x = pts['d_trans'].values
            y = pts['d_long'].values
            s = np.abs(pts['settlement_full'].values)
            #s = np.abs(pts['settlement_safe'].values)
            
            # Autodetekcja jednostek (jeśli max < 1, to prawdopodobnie są metry -> na mm)
            if np.max(s) < 1.0: 
                s = s * 1000 

            try:
                # --- INTERPOLACJA POWIERZCHNIOWA ---
                # Tworzymy siatkę punktów co 1 metr
                grid_x, grid_y = np.mgrid[-ZONE_TRANS:ZONE_TRANS:1.0, 
                                          ZONE_LONG[0]:ZONE_LONG[1]:1.0]

                # Interpolacja liniowa (metoda namiotu)
                # fill_value=0 realizuje Twoje założenie: brak danych = brak osiadania
                grid_s = griddata((x, y), s, (grid_x, grid_y), method='linear', fill_value=0)

                # --- CAŁKOWANIE OBJĘTOŚCI ---
                # Objętość bryły w [mm * m2]. Dzielimy przez 1000, by dostać [m3]
                # Pole jednej komórki siatki to 1.0m * 1.0m = 1.0
                total_v_settlement = np.sum(grid_s / 1000.0) * 1.0
                
                # Obliczamy objętość na 1 metr bieżący tunelu
                zone_length = ZONE_LONG[1] - ZONE_LONG[0]
                v_s_per_meter = total_v_settlement / zone_length
                
                # Obliczamy V_loss [%]
                v_loss_pct = (v_s_per_meter / v_tunnel_nominal) * 100
                s_max_mm = np.max(grid_s)

                # Filtracja nierealnych wyników (powyżej 5% to zazwyczaj błąd czujnika)
                if v_loss_pct > 5.0: v_loss_pct = 5.0

                res_dict = ring.to_dict()
                res_dict.update({
                    'target_s_max_mm': s_max_mm,
                    'target_v_loss': v_loss_pct,
                    'pts_count': len(pts)
                })
                final_results.append(res_dict)

            except Exception as e:
                # W razie błędu obliczeń dla ringu, pomijamy go
                continue

    # Zapis wyników
    if final_results:
        df_final = pd.DataFrame(final_results)
        df_final.to_csv(OUTPUT_PATH, index=False)
        
        print("-" * 30)
        print(f"SUKCES! Przetworzono {len(df_final)} ringów.")
        print(f"Średni V_loss: {df_final['target_v_loss'].mean():.4f}%")
        print(f"Średnie S_max: {df_final['target_s_max_mm'].mean():.2f} mm")
        print(f"Wyniki zapisano w: {OUTPUT_PATH}")
        print("-" * 30)
    else:
        print("Nie udało się wygenerować żadnych wyników. Sprawdź zasięg stref (ZONE)!")

if __name__ == "__main__":
    calculate_vloss_griddata()