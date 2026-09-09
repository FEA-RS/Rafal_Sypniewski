import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.interpolate import Rbf
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
    #'out': r"D:\%PRACA_MAGISTERSKA\results\raport_profesor\Method_D_Kriging"
    'out': r"D:\%PRACA_MAGISTERSKA\data\interim\V_loss_ML.parquet"
}

os.makedirs(PATHS['out'], exist_ok=True)

def run_kriging_report():
    print("--- START ANALIZY METODĄ D (KRIGING RBF) ---")
    df_tbm = pd.read_parquet(PATHS['tbm']).sort_values('ring')
    df_sensors = pd.read_parquet(PATHS['sensors'])
    df_tbm['date'] = pd.to_datetime(df_tbm['timestamp']).dt.date
    df_sensors['date'] = pd.to_datetime(df_sensors['date']).dt.date
    
    v_tunnel = (np.pi * SHIELD_DIAMETER**2) / 4
    x_grid = np.linspace(-WINDOW_TRANS, WINDOW_TRANS, 200) # Gęsta siatka co 0.3m
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
        if len(pts_ring) < 4: continue # Kriging potrzebuje min. kilku punktów

        # 2. Peak Tracking + Heave Removal (Clamping)
        def clean_settlement(s):
            return -s if s < 0 else 0

        #pts_ring['s_mm'] = pts_ring['settlement_full'].apply(clean_settlement)
        pts_ring['s_mm'] = pts_ring['settlement_safe'].apply(clean_settlement)
        pts_peak = pts_ring.groupby('sensor_id').agg({'d_trans': 'mean', 's_mm': 'max'}).reset_index()

        x_data = pts_peak['d_trans'].values
        y_data = pts_peak['s_mm'].values

        # --- METODA : KRIGING (RBF INTERPOLATION) ---
        try:
            # RBF z funkcją multiquadric działa jak Kriging, wygładzając szum (smooth=0.1)
            rbf = Rbf(x_data, y_data, function='multiquadric', smooth=0.1)
            y_pred = rbf(x_grid)
            
            # FILTR "BELOW ZERO": Ucinamy wszystko co wystaje ponad grunt
            y_pred_clamped = np.maximum(y_pred, 0)
            
            # Integracja numeryczna na wygładzonej powierzchni
            v_s_d = np.trapz(y_pred_clamped / 1000, x_grid)
            v_d = (v_s_d / v_tunnel) * 100
            
            # Zapis wykresu
            plt.figure(figsize=(8,4))
            plt.fill_between(x_grid, y_pred_clamped, color='purple', alpha=0.2, label='Objętość Vloss (Kriging)')
            plt.scatter(x_data, y_data, color='black', s=10, label='Pomiary (Peak)')
            plt.plot(x_grid, y_pred, 'p--', alpha=0.2, label='Trend RAW')
            plt.title(f"Ring {int(ring['ring'])} |  Kriging | Vloss: {v_d:.3f}%")
            plt.gca().invert_yaxis(); plt.grid(True, alpha=0.2); plt.legend()
            plt.savefig(os.path.join(PATHS['out'], f"ring_{int(ring['ring'])}.png")); plt.close()
            
            report_list.append({'ring': ring['ring'], 'D_Vloss': v_d, 'D_Smax': np.max(y_pred_clamped)})
        except:
            report_list.append({'ring': ring['ring'], 'D_Vloss': np.nan, 'D_Smax': np.nan})

    df_res = pd.DataFrame(report_list)
    df_res.to_parquet(os.path.join(PATHS['out'], "raport_Metoda_D_Kriging.parquet"), index=False)
    print(f"\nŚredni V_loss (Metoda D): {df_res['D_Vloss'].mean():.3f}%")

if __name__ == "__main__":
    run_kriging_report()