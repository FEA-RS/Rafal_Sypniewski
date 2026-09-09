import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os
import warnings

warnings.filterwarnings("ignore")

# --- TWOJE KLUCZOWE PARAMETRY ---
SHIELD_DIAMETER = 13.0
WINDOW_LONG = [-SHIELD_DIAMETER, 1.5*SHIELD_DIAMETER] # [za, przed] 
WINDOW_TRANS = 5*SHIELD_DIAMETER/2       
TIME_WINDOW_DAYS = 0    # Zoptymalizowane okno 3-dniowe

PATHS = {
    'tbm': r"D:\%PRACA_MAGISTERSKA\data\interim\tbm_features_ring.parquet",
    'sensors': r"D:\%PRACA_MAGISTERSKA\data\interim\sensors_interpolated.parquet",
    # 'out': r"D:\%PRACA_MAGISTERSKA\results\raport_profesor\Method_B_Calka"
    'out': r"D:\%PRACA_MAGISTERSKA\data\interim\V_loss_ML_2.parquet"
}

os.makedirs(PATHS['out'], exist_ok=True)

def run_integration_report():
    print("--- START ANALIZY METODĄ B (INTEGRACJA 1D / CAŁKA) ---")
    df_tbm = pd.read_parquet(PATHS['tbm']).sort_values('ring')
    df_sensors = pd.read_parquet(PATHS['sensors'])
    df_tbm['date'] = pd.to_datetime(df_tbm['timestamp']).dt.date
    df_sensors['date'] = pd.to_datetime(df_sensors['date']).dt.date
    
    v_tunnel = (np.pi * SHIELD_DIAMETER**2) / 4
    report_list = []

    for idx in range(len(df_tbm)):
        ring = df_tbm.iloc[idx]
        ring_date = ring['date']
        
        # 1. Filtrowanie (Twoje okna czasowe i przestrzenne)
        mask_time = (df_sensors['date'] >= ring_date) & (df_sensors['date'] <= ring_date + pd.Timedelta(days=TIME_WINDOW_DAYS))
        pts = df_sensors[mask_time].copy()
        if pts.empty: continue

        # [Logika rotacji współrzędnych - d_long i d_trans]
        if idx < len(df_tbm)-1:
            next_r = df_tbm.iloc[idx+1]
            bearing = np.arctan2(next_r['longitude'] - ring['longitude'], next_r['latitude'] - ring['latitude'])
        else: bearing = 0 

        d_lat = (pts['latitude'] - ring['latitude']) * 111132
        d_lon = (pts['longitude'] - ring['longitude']) * 71000
        pts['d_trans'] = d_lon * np.cos(bearing) - d_lat * np.sin(bearing)
        pts['d_long'] = d_lon * np.sin(bearing) + d_lat * np.cos(bearing)

        pts_ring = pts[(pts['d_long'] >= WINDOW_LONG[0]) & (pts['d_long'] <= WINDOW_LONG[1]) & (np.abs(pts['d_trans']) <= WINDOW_TRANS)].copy()
        if len(pts_ring) < 2: continue # Integracja potrzebuje min. 2 punktów

        # 2. Peak Tracking + Heave Removal (Clamping)
        def clean_settlement(s):
            return -s if s < 0 else 0

        #pts_ring['s_mm'] = pts_ring['settlement_full'].apply(clean_settlement)
        pts_ring['s_mm'] = pts_ring['settlement_safe'].apply(clean_settlement)
        pts_peak = pts_ring.groupby('sensor_id').agg({'d_trans': 'mean', 's_mm': 'max'}).reset_index()

        x_data = pts_peak['d_trans'].values
        y_data = pts_peak['s_mm'].values

        # --- METODA B: INTEGRACJA 1D ---
        try:
            # Sortowanie wektorów przed wykonaniem całki (wymóg np.trapz)
            sort_idx = np.argsort(x_data)
            x_sorted = x_data[sort_idx]
            y_sorted = y_data[sort_idx]
            
            # Integracja numeryczna bezpośrednio po wyznaczonych peakach
            v_s_b = np.trapz(y_sorted / 1000, x_sorted) 
            v_b = (v_s_b / v_tunnel) * 100
            
            # Zapis wykresu
            plt.figure(figsize=(8,4))
            plt.fill_between(x_sorted, y_sorted, color='orange', alpha=0.2, label='Objętość Vloss (Całka 1D)')
            plt.plot(x_sorted, y_sorted, 'o-', color='black', markersize=4, label='Pomiary (Peak)')
            plt.title(f"Ring {int(ring['ring'])} |  Integracja 1D | Vloss: {v_b:.3f}%")
            plt.gca().invert_yaxis(); plt.grid(True, alpha=0.2); plt.legend()
            plt.savefig(os.path.join(PATHS['out'], f"ring_{int(ring['ring'])}.png")); plt.close()
            
            report_list.append({'ring': ring['ring'], 'D_Vloss': v_b, 'B_Smax': np.max(y_sorted)})
        except:
            report_list.append({'ring': ring['ring'], 'D_Vloss': np.nan, 'B_Smax': np.nan})

    df_res = pd.DataFrame(report_list)
    df_res.to_parquet(os.path.join(PATHS['out'], "raport_Metoda_B_Calka.parquet"), index=False)
    print(f"\nŚredni V_loss (Metoda B): {df_res['D_Vloss'].mean():.3f}%")

if __name__ == "__main__":
    run_integration_report()