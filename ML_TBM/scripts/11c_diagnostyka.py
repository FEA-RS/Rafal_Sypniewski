import pandas as pd
import numpy as np

PATH_TBM = r"D:\%PRACA_MAGISTERSKA\data\interim\tbm_features_ring.parquet"
PATH_SENSORS = r"D:\%PRACA_MAGISTERSKA\data\interim\sensors_interpolated.parquet"

def debug_data():
    print("--- START DIAGNOSTYKI ---")
    df_tbm = pd.read_parquet(PATH_TBM).sort_values('ring')
    df_sensors = pd.read_parquet(PATH_SENSORS)
    
    # Sprawdźmy formaty dat
    print(f"Format daty TBM: {type(df_tbm['timestamp'].iloc[0])}")
    print(f"Przykładowa data TBM: {df_tbm['timestamp'].iloc[0]}")
    
    df_tbm['date'] = pd.to_datetime(df_tbm['timestamp']).dt.date
    df_sensors['date'] = pd.to_datetime(df_sensors['date']).dt.date
    
    print(f"Unikalne daty w TBM (pierwsze 5): {df_tbm['date'].unique()[:10]}")
    print(f"Unikalne daty w Sensors (pierwsze 5): {df_sensors['date'].unique()[:10]}")
    
    # Wybieramy ring, który na 100% powinien mieć dane (np. ze środka budowy)
    test_ring_id = 138 
    ring = df_tbm[df_tbm['ring'] == test_ring_id].iloc[0]
    
    print(f"\nAnaliza Ringu {test_ring_id}:")
    print(f"Data ringu: {ring['date']}")
    print(f"Pozycja: Lat {ring['latitude']}, Lon {ring['longitude']}")
    
    # Szukamy czujników w tym samym dniu
    day_sensors = df_sensors[df_sensors['date'] == ring['date']]
    print(f"Liczba czujników w bazie na ten dzień: {len(day_sensors)}")
    
    if len(day_sensors) > 0:
        # Sprawdzamy surowy dystans w stopniach (czy w ogóle są w tej samej okolicy)
        d_lat = day_sensors['latitude'] - ring['latitude']
        d_lon = day_sensors['longitude'] - ring['longitude']
        dist_deg = np.sqrt(d_lat**2 + d_lon**2)
        
        # Przeliczamy na metry (orientacyjnie)
        dist_m = dist_deg * 100000
        print(f"Czujniki w promieniu 500m (surowo): {len(day_sensors[dist_m < 100])}")
        
        if len(day_sensors[dist_m < 500]) > 0:
            sample = day_sensors[dist_m < 500].iloc[0]
            print(f"Przykładowy czujnik blisko: {sample['sensor_id']}, Osiadanie: {sample['settlement_full']}")
    else:
        print("BŁĄD: Brak jakichkolwiek odczytów czujników w dniu tego ringu!")

if __name__ == "__main__":
    debug_data()