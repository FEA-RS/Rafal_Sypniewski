import pandas as pd
import numpy as np
import os

PATH_INPUT = r"D:\%PRACA_MAGISTERSKA\data\interim\sensors_readings_spatial.parquet"
PATH_OUTPUT = r"D:\%PRACA_MAGISTERSKA\data\interim\sensors_interpolated.parquet"
PATH_REPORT = r"D:\%PRACA_MAGISTERSKA\results\reports\interpolation_report.txt"
GAP_LIMIT_DAYS = 0 

def interpolate_sensors():
    print("Wczytuję dane...")
    df = pd.read_parquet(PATH_INPUT)
    df['date'] = pd.to_datetime(df['timestamp']).dt.date
    df = df.groupby(['sensor_id', 'date', 'latitude', 'longitude'])['settlement_value'].mean().reset_index()
    
    interpolated_frames = []
    sensors = df['sensor_id'].unique()
    
    # Statystyki do raportu
    stats = []

    print(f"Przetwarzam {len(sensors)} czujników...")
    for s_id in sensors:
        s_data = df[df['sensor_id'] == s_id].copy().sort_values('date')
        lat, lon = s_data['latitude'].iloc[0], s_data['longitude'].iloc[0]
        
        full_range = pd.date_range(start=s_data['date'].min(), end=s_data['date'].max(), freq='D').date
        s_resampled = pd.DataFrame({'date': full_range})
        s_resampled = s_resampled.merge(s_data[['date', 'settlement_value']], on='date', how='left')
        
        # Obliczanie luk przed interpolacją
        is_measured = s_resampled['settlement_value'].notna()
        max_gap = (~is_measured).groupby(is_measured.cumsum()).cumsum().max()
        
        # FULL
        s_resampled['settlement_full'] = s_resampled['settlement_value'].interpolate(method='linear')
        
        # SAFE
        gap_sizes = (~is_measured).groupby(is_measured.cumsum()).cumsum()
        s_resampled['settlement_safe'] = s_resampled['settlement_full']
        s_resampled.loc[gap_sizes > GAP_LIMIT_DAYS, 'settlement_safe'] = np.nan
        
        s_resampled['sensor_id'], s_resampled['latitude'], s_resampled['longitude'] = s_id, lat, lon
        interpolated_frames.append(s_resampled)
        
        stats.append({
            'sensor_id': s_id,
            'days_total': len(s_resampled),
            'actual_measures': is_measured.sum(),
            'max_gap_days': max_gap,
            'full_count': s_resampled['settlement_full'].notna().sum(),
            'safe_count': s_resampled['settlement_safe'].notna().sum()
        })

    # Zapis danych
    df_final = pd.concat(interpolated_frames)
    df_final.to_parquet(PATH_OUTPUT, index=False)
    
    # Generowanie raportu tekstowego
    df_stats = pd.DataFrame(stats)
    os.makedirs(os.path.dirname(PATH_REPORT), exist_ok=True)
    
    with open(PATH_REPORT, 'w') as f:
        f.write("RAPORT INTERPOLACJI MONITORINGU\n")
        f.write("="*40 + "\n")
        f.write(f"Liczba czujników: {len(sensors)}\n")
        f.write(f"Srednia luka pomiarowa: {df_stats['max_gap_days'].mean():.2f} dni\n")
        f.write(f"Najdluzsza luka: {df_stats['max_gap_days'].max()} dni\n")
        f.write(f"Pokrycie FULL: {df_stats['full_count'].sum() / df_stats['days_total'].sum():.1%}\n")
        f.write(f"Pokrycie SAFE (limit {GAP_LIMIT_DAYS}d): {df_stats['safe_count'].sum() / df_stats['days_total'].sum():.1%}\n")
        f.write(f"Utrata danych w SAFE: {1 - (df_stats['safe_count'].sum() / df_stats['full_count'].sum()):.1%}\n")

    print(f"Zakończono. Raport zapisany w: {PATH_REPORT}")

if __name__ == "__main__":
    interpolate_sensors()