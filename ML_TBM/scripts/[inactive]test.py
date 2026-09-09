import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.optimize import curve_fit
import os
import warnings

warnings.filterwarnings("ignore")

# --- PARAMETRY WEJŚCIOWE ---
SHIELD_DIAMETER = 13.0
WINDOW_LONG = [-SHIELD_DIAMETER, 1.5*SHIELD_DIAMETER] # [za, przed] 
WINDOW_TRANS = 5*SHIELD_DIAMETER/2       
TIME_WINDOW_DAYS = 0    # Zoptymalizowane okno 3-dniowe        

PATHS = {
    'tbm': r"D:\%PRACA_MAGISTERSKA\data\interim\tbm_features_ring.parquet",
    'sensors': r"D:\%PRACA_MAGISTERSKA\data\interim\sensors_interpolated.parquet",
    'out': r"D:\%PRACA_MAGISTERSKA\results\raport_profesor"
}

# Inicjalizacja struktury folderów
folders = ['Method_A_Gauss', 'Method_B_Integration', 'Method_C_Statistical']
for f in folders:
    os.makedirs(os.path.join(PATHS['out'], f), exist_ok=True)

def peck_func_with_offset(x, s_max, i, x0):
    return s_max * np.exp(-((x - x0)**2) / (2 * i**2))

def run_vloss_comparison():
    print("--- START ANALIZY PORÓWNAWCZEJ V_LOSS (PEAK TRACKING + HEAVE REMOVAL) ---")
    df_tbm = pd.read_parquet(PATHS['tbm']).sort_values('ring')
    df_sensors = pd.read_parquet(PATHS['sensors'])
    df_tbm['date'] = pd.to_datetime(df_tbm['timestamp']).dt.date
    df_sensors['date'] = pd.to_datetime(df_sensors['date']).dt.date
    
    v_tunnel = (np.pi * SHIELD_DIAMETER**2) / 4
    report_list = []

    for idx in range(len(df_tbm)):
        ring = df_tbm.iloc[idx]
        ring_date = ring['date']
        
        mask_time = (df_sensors['date'] >= ring_date) & (df_sensors['date'] <= ring_date + pd.Timedelta(days=TIME_WINDOW_DAYS))
        pts = df_sensors[mask_time].copy()
        if pts.empty: continue

        if idx < len(df_tbm)-1:
            next_r = df_tbm.iloc[idx+1]
            bearing = np.arctan2(next_r['longitude'] - ring['longitude'], next_r['latitude'] - ring['latitude'])
        else:
            bearing = 0 

        d_lat = (pts['latitude'] - ring['latitude']) * 111132
        d_lon = (pts['longitude'] - ring['longitude']) * 71000
        pts['d_trans'] = d_lon * np.cos(bearing) - d_lat * np.sin(bearing)
        pts['d_long'] = d_lon * np.sin(bearing) + d_lat * np.cos(bearing)

        pts_ring = pts[(pts['d_long'] >= WINDOW_LONG[0]) & 
                        (pts['d_long'] <= WINDOW_LONG[1]) & 
                        (np.abs(pts['d_trans']) <= WINDOW_TRANS)].copy()
        
        if len(pts_ring) < 5: continue

        # --- KLUCZOWA ZMIANA: REZYGNACJA Z ABS() NA RZECZ CLAMPINGU ---
        # Zakładamy: settlement_full < 0 to osiadanie (w dół)
        # Zamieniamy na dodatnie mm, ale wszystko co było > 0 (wypiętrzenie) zmieniamy na 0.
        def clean_settlement(s):
            val = s * 1000 if abs(s) < 0.2 else s
            return -val if val < 0 else 0  # Tylko wartości ujemne stają się dodatnim osiadaniem

        #pts_ring['s_mm'] = pts_ring['settlement_full'].apply(clean_settlement)
        pts_ring['s_mm'] = pts_ring['settlement_safe'].apply(clean_settlement)

        pts_peak = pts_ring.groupby('sensor_id').agg({
            'd_trans': 'mean',
            's_mm': 'max'
        }).reset_index()

        x = pts_peak['d_trans'].values
        y = pts_peak['s_mm'].values
        
        # Dodatkowe zabezpieczenie: y musi być >= 0
        y = np.maximum(y, 0)

        # --- METODA A: DOŻYŁOWANY GAUSS FIT ---
        try:
            s_start = np.percentile(y, 95)
            popt, _ = curve_fit(
                peck_func_with_offset, x, y, 
                p0=[s_start, 15.0, 0.0], 
                bounds=([0.1, 10.0, -5.0], [200.0, 40.0, 5.0]),
                sigma=np.where(y > (s_start * 0.5), 0.5, 1.0),
                maxfev=10000, 
                method='trf'
            )
            s_a, i_a, x0_a = popt
            v_a = (np.sqrt(2*np.pi) * i_a * (s_a/1000) / v_tunnel) * 100
            
            plt.figure(figsize=(7,4))
            plt.scatter(x, y, alpha=0.4, s=10, label='Dane (osiadania)')
            x_range = np.linspace(-WINDOW_TRANS, WINDOW_TRANS, 100)
            plt.plot(x_range, peck_func_with_offset(x_range, *popt), 'r', label='Gauss Fit')
            plt.title(f"Ring {int(ring['ring'])} | A: Gauss | Vloss: {v_a:.3f}%")
            plt.gca().invert_yaxis(); plt.grid(True, alpha=0.2); plt.legend()
            plt.savefig(os.path.join(PATHS['out'], folders[0], f"ring_{int(ring['ring'])}.png")); plt.close()
        except: s_a, i_a, v_a = np.nan, np.nan, np.nan

        # --- METODA B: INTEGRACJA ---
        sort_idx = np.argsort(x)
        # Teraz y zawiera tylko wartości >= 0 (czysta dziura)
        v_s_b = np.trapz(y[sort_idx]/1000, x[sort_idx]) 
        v_b = (v_s_b / v_tunnel) * 100
        
        plt.figure(figsize=(7,4)); plt.fill_between(x[sort_idx], y[sort_idx], color='green', alpha=0.2); plt.scatter(x, y, s=10)
        plt.title(f"Ring {int(ring['ring'])} - B: Integracja | Vloss: {v_b:.3f}%"); plt.gca().invert_yaxis()
        plt.savefig(os.path.join(PATHS['out'], folders[1], f"ring_{int(ring['ring'])}.png")); plt.close()

        # --- METODA C: STATYSTYCZNA (WSD) ---
        s_c = np.percentile(y, 95)
        sum_y = np.sum(y)
        weights = y / sum_y if sum_y > 0 else np.ones(len(y))/len(y)
        i_c = np.sqrt(np.sum(weights * (x**2)))
        v_c = (np.sqrt(2*np.pi) * i_c * (s_c/1000) / v_tunnel) * 100

        plt.figure(figsize=(7,4)); plt.scatter(x, y, color='orange', alpha=0.5); plt.axvspan(-i_c, i_c, alpha=0.1, color='orange')
        plt.title(f"Ring {int(ring['ring'])} - C: Stat | Vloss: {v_c:.3f}%"); plt.gca().invert_yaxis()
        plt.savefig(os.path.join(PATHS['out'], folders[2], f"ring_{int(ring['ring'])}.png")); plt.close()

        report_list.append({
            'ring': ring['ring'],
            'A_Vloss': v_a, 'A_Smax': s_a, 'A_i': i_a,
            'B_Vloss': v_b,
            'C_Vloss': v_c, 'C_Smax': s_c, 'C_i': i_c,
            'pts_count': len(pts_peak)
        })

    df_final = pd.DataFrame(report_list)
    df_final.to_csv(os.path.join(PATHS['out'], "raport_Vloss_PeakTracking.csv"), index=False)
    
    print("\n--- PODSUMOWANIE ŚREDNIE (HEAVE REMOVED) ---")
    print(df_final[['A_Vloss', 'B_Vloss', 'C_Vloss']].mean())

if __name__ == "__main__":
    run_vloss_comparison()