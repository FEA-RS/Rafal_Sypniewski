import pandas as pd
import numpy as np
import os

# 1. CONFIGURATION
PATH_TBM = r"D:\%PRACA_MAGISTERSKA\data\interim\tbm_features_ring.parquet"
PATH_SENSORS = r"D:\%PRACA_MAGISTERSKA\data\interim\sensors_interpolated.parquet"
PATH_AUDIT_CSV = r"D:\%PRACA_MAGISTERSKA\results\reports\ring_audit_detailed.csv"
PATH_AUDIT_SUMMARY = r"D:\%PRACA_MAGISTERSKA\results\reports\ring_audit_summary.txt"


WINDOW_LONGITUDINAL = [-3*13, 2*13] # meters behind and ahead of the TBM shield
WINDOW_TRANSVERSE = 26+13          # meters sideways from the tunnel axis

def audit_rings_window():
    print("Starting audit in calculation window (matching settlement trough parameters)...")
    
    # Load and sort datasets
    df_tbm = pd.read_parquet(PATH_TBM).sort_values('ring')
    df_sensors = pd.read_parquet(PATH_SENSORS)
    
    df_tbm['date'] = pd.to_datetime(df_tbm['timestamp']).dt.date
    df_sensors['date'] = pd.to_datetime(df_sensors['date']).dt.date

    results = []
    bearing = 0  # Initialize direction

    for i in range(len(df_tbm)):
        ring = df_tbm.iloc[i]
        
        # Determine tunnel direction (bearing)
        if i < len(df_tbm) - 1:
            next_r = df_tbm.iloc[i+1]
            bearing = np.arctan2(next_r['longitude'] - ring['longitude'], next_r['latitude'] - ring['latitude'])
        
        # Filter sensors measured on the same day as the ring construction
        day_sensors = df_sensors[df_sensors['date'] == ring['date']].copy()
        
        if day_sensors.empty:
            results.append({
                'ring': int(ring['ring']), 'date': ring['date'], 
                'pts_total': 0, 'pts_full': 0, 'pts_safe': 0, 'status': 'NO DATA'
            })
            continue

        # 1. Coordinate transformation to meters
        d_lat = (day_sensors['latitude'] - ring['latitude']) * 111132
        d_lon = (day_sensors['longitude'] - ring['longitude']) * 71000
        
        # 2. Rotation to TBM local coordinate system (X=transverse, Y=longitudinal)
        dist_trans = d_lon * np.cos(bearing) - d_lat * np.sin(bearing)
        dist_long = d_lon * np.sin(bearing) + d_lat * np.cos(bearing)

        # 3. Window filtration
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
            'status': 'OK' if count_safe >= 4 else 'INSUFFICIENT POINTS (SAFE)'
        })

    # Save detailed results
    audit_df = pd.DataFrame(results).sort_values('ring')
    os.makedirs(os.path.dirname(PATH_AUDIT_CSV), exist_ok=True)
    audit_df.to_csv(PATH_AUDIT_CSV, index=False)
    
    # Calculate statistics
    rings_ok = len(audit_df[audit_df['pts_safe'] >= 4])
    
    # Generate summary report
    with open(PATH_AUDIT_SUMMARY, 'w') as f:
        f.write("CALCULATION WINDOW AUDIT\n")
        f.write(f"Longitudinal range: {WINDOW_LONGITUDINAL} m\n")
        f.write(f"Transverse range: +/- {WINDOW_TRANSVERSE} m\n")
        f.write("-" * 30 + "\n")
        f.write(f"Total rings analyzed: {len(audit_df)}\n")
        f.write(f"Rings with min. 4 points (SAFE): {rings_ok} ({rings_ok/len(audit_df):.1%})\n")
        f.write(f"Average points per ring (SAFE): {audit_df['pts_safe'].mean():.1f}\n")

    print(f"Window audit completed. Ready rings: {rings_ok}/{len(audit_df)}")

if __name__ == "__main__":
    audit_rings_window()