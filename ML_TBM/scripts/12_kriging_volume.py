import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.interpolate import Rbf
import os
import warnings

warnings.filterwarnings("ignore")

# --- KEY PARAMETERS ---
SHIELD_DIAMETER = 13.0
WINDOW_LONG = [-3*13, 2*13] 
WINDOW_TRANS = 26 + 13/2       
TIME_WINDOW_DAYS = 0    #  time window

PATHS = {
    'tbm': r"D:\%PRACA_MAGISTERSKA\data\interim\tbm_features_ring.parquet",
    'sensors': r"D:\%PRACA_MAGISTERSKA\data\interim\sensors_interpolated.parquet",
    'out': r"D:\%PRACA_MAGISTERSKA\results\raport_profesor\Method_D_Kriging"
}

os.makedirs(PATHS['out'], exist_ok=True)

def run_kriging_report():
    print("--- STARTING ANALYSIS: METHOD D (KRIGING RBF) ---")
    
    # Load data
    df_tbm = pd.read_parquet(PATHS['tbm']).sort_values('ring')
    df_sensors = pd.read_parquet(PATHS['sensors'])
    
    df_tbm['date'] = pd.to_datetime(df_tbm['timestamp']).dt.date
    df_sensors['date'] = pd.to_datetime(df_sensors['date']).dt.date
    
    # Tunnel cross-section area: (PI * D^2) / 4
    v_tunnel = (np.pi * SHIELD_DIAMETER**2) / 4
    
    # Dense grid for integration (approx. every 0.3m)
    x_grid = np.linspace(-WINDOW_TRANS, WINDOW_TRANS, 200) 
    report_list = []

    for idx in range(len(df_tbm)):
        ring = df_tbm.iloc[idx]
        ring_date = ring['date']
        
        # 1. Temporal and Spatial Filtering
        mask_time = (df_sensors['date'] >= ring_date) & \
                    (df_sensors['date'] <= ring_date + pd.Timedelta(days=TIME_WINDOW_DAYS))
        pts = df_sensors[mask_time].copy()
        if pts.empty: 
            continue

        # Coordinate Rotation Logic (Longitudinal and Transverse)
        if idx < len(df_tbm) - 1:
            next_r = df_tbm.iloc[idx+1]
            bearing = np.arctan2(next_r['longitude'] - ring['longitude'], 
                                 next_r['latitude'] - ring['latitude'])
        else: 
            bearing = 0 

        d_lat = (pts['latitude'] - ring['latitude']) * 111132
        d_lon = (pts['longitude'] - ring['longitude']) * 71000
        pts['d_trans'] = d_lon * np.cos(bearing) - d_lat * np.sin(bearing)
        pts['d_long'] = d_lon * np.sin(bearing) + d_lat * np.cos(bearing)

        # Filter points within the calculation window
        pts_ring = pts[(pts['d_long'] >= WINDOW_LONG[0]) & 
                        (pts['d_long'] <= WINDOW_LONG[1]) & 
                        (np.abs(pts['d_trans']) <= WINDOW_TRANS)].copy()
        
        if len(pts_ring) < 6: 
            continue # Kriging requires a minimum point density

        # 2. Peak Tracking & Heave Removal (Clamping)
        def clean_settlement(s):
            # Convert to mm and handle potential outliers
            val = s * 1000 if abs(s) < 0.2 else s
            # Reverse sign: settlement should be positive for volume calculation
            return -val if val < 0 else 0 

        pts_ring['s_mm'] = pts_ring['settlement_safe'].apply(clean_settlement)
        pts_peak = pts_ring.groupby('sensor_id').agg({'d_trans': 'mean', 's_mm': 'max'}).reset_index()

        x_data = pts_peak['d_trans'].values
        y_data = pts_peak['s_mm'].values

        # --- METHOD: KRIGING (RBF INTERPOLATION) ---
        try:
            # RBF with multiquadric function smoothed to handle noise (smooth=0.1)
            rbf = Rbf(x_data, y_data, function='multiquadric', smooth=0.1)
            y_pred = rbf(x_grid)
            
            # "Below Zero" Filter: Remove values above ground level (heave)
            y_pred_clamped = np.maximum(y_pred, 0)
            
            # Numerical integration of the smoothed surface (Trapezoidal rule)
            v_s_d = np.trapz(y_pred_clamped / 1000, x_grid)
            v_loss_percentage = (v_s_d / v_tunnel) * 100
            
            # Visualization
            plt.figure(figsize=(8,4))
            plt.fill_between(x_grid, y_pred_clamped, color='purple', alpha=0.2, label='$V_{loss}$ (Kriging)')
            plt.scatter(x_data, y_data, color='black', s=10, label='Measurements (Peak)')
            plt.plot(x_grid, y_pred, 'p--', alpha=0.2, label='Raw Trend')
            plt.title(f"Ring {int(ring['ring'])} | Kriging | $V_{{loss}}$: {v_loss_percentage:.3f}%")
            plt.gca().invert_yaxis()
            plt.grid(True, alpha=0.2)
            plt.legend()
            plt.savefig(os.path.join(PATHS['out'], f"ring_{int(ring['ring'])}.png"))
            plt.close()
            
            report_list.append({
                'ring': ring['ring'], 
                'D_Vloss': v_loss_percentage, 
                'D_Smax': np.max(y_pred_clamped)
            })
        except Exception:
            report_list.append({
                'ring': ring['ring'], 
                'D_Vloss': np.nan, 
                'D_Smax': np.nan
            })

    # Save final report
    df_res = pd.DataFrame(report_list)
    df_res.to_csv(os.path.join(PATHS['out'], "report_Method_D_Kriging.csv"), index=False)
    print(f"\nMean $V_{{loss}}$ (Method D): {df_res['D_Vloss'].mean():.3f}%")

if __name__ == "__main__":
    run_kriging_report()