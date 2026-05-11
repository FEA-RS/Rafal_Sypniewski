import pandas as pd
import numpy as np

# 1. PATH CONFIGURATION
PATH_TBM = r"D:\%PRACA_MAGISTERSKA\data\interim\tbm_features_ring.parquet"
PATH_SENSORS = r"D:\%PRACA_MAGISTERSKA\data\interim\sensors_interpolated.parquet"

def debug_data():
    print("--- STARTING DIAGNOSTICS ---")
    
    # Load and sort data
    df_tbm = pd.read_parquet(PATH_TBM).sort_values('ring')
    df_sensors = pd.read_parquet(PATH_SENSORS)
    
    # Verify date formats and sample entries
    print(f"TBM date format: {type(df_tbm['timestamp'].iloc[0])}")
    print(f"TBM sample date: {df_tbm['timestamp'].iloc[0]}")
    
    df_tbm['date'] = pd.to_datetime(df_tbm['timestamp']).dt.date
    df_sensors['date'] = pd.to_datetime(df_sensors['date']).dt.date
    
    print(f"Unique dates in TBM (first 10): {df_tbm['date'].unique()[:10]}")
    print(f"Unique dates in Sensors (first 10): {df_sensors['date'].unique()[:10]}")
    
    # Select a test ring likely to have valid data
    test_ring_id = 138 
    ring = df_tbm[df_tbm['ring'] == test_ring_id].iloc[0]
    
    print(f"\nAnalysis for Ring {test_ring_id}:")
    print(f"Ring date: {ring['date']}")
    print(f"Position: Lat {ring['latitude']}, Lon {ring['longitude']}")
    
    # Search for sensors active on the same date
    day_sensors = df_sensors[df_sensors['date'] == ring['date']]
    print(f"Number of sensors found for this date: {len(day_sensors)}")
    
    if len(day_sensors) > 0:
        # Check raw distance in degrees to verify spatial proximity
        d_lat = day_sensors['latitude'] - ring['latitude']
        d_lon = day_sensors['longitude'] - ring['longitude']
        dist_deg = np.sqrt(d_lat**2 + d_lon**2)
        
        # Approximate conversion to meters for verification
        dist_m = dist_deg * 100000
        print(f"Sensors within 100m radius (raw): {len(day_sensors[dist_m < 100])}")
        
        if len(day_sensors[dist_m < 500]) > 0:
            sample = day_sensors[dist_m < 500].iloc[0]
            print(f"Sample nearby sensor: {sample['sensor_id']}, Settlement: {sample['settlement_full']}")
    else:
        print("ERROR: No sensor readings found for this ring's date!")

if __name__ == "__main__":
    debug_data()