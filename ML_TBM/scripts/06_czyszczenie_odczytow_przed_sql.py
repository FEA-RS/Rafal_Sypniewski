import pandas as pd
import os

# Ścieżki plików
PATH_READINGS = r"D:\%PRACA_MAGISTERSKA\data\interim\new_readings_to_import.csv"
PATH_META = r"D:\%PRACA_MAGISTERSKA\data\interim\sensors_metadata_v2.csv"
PATH_CLEANED_OUT = r"D:\%PRACA_MAGISTERSKA\data\interim\readings_FOR_SQL_FINAL.csv"

def wyczysc_plik_do_sql():
    print("Rozpoczynam filtrowanie danych... To może chwilę potrwać (3.8 mln rekordów).")
    
    # 1. Wczytujemy poprawne ID z metadanych (to jest nasza 'biała lista')
    df_meta = pd.read_csv(PATH_META, usecols=['sensor_id'])
    valid_ids = set(df_meta['sensor_id'].unique())
    
    # 2. Przetwarzamy odczyty w paczkach (chunks), aby nie zapchać RAMu
    chunk_size = 500000
    first_chunk = True
    total_cleaned = 0
    total_original = 0
    
    for chunk in pd.read_csv(PATH_READINGS, chunksize=chunk_size):
        total_original += len(chunk)
        
        # Filtrujemy: zostawiamy tylko te wiersze, których sensor_id jest w metadanych
        cleaned_chunk = chunk[chunk['sensor_id'].isin(valid_ids)]
        total_cleaned += len(cleaned_chunk)
        
        # Zapisujemy do nowego pliku (za pierwszym razem z nagłówkiem, potem dopisujemy)
        if first_chunk:
            cleaned_chunk.to_csv(PATH_CLEANED_OUT, index=False, mode='w')
            first_chunk = False
        else:
            cleaned_chunk.to_csv(PATH_CLEANED_OUT, index=False, mode='a', header=False)
            
        print(f"Przetworzono: {total_original} wierszy...")

    print("-" * 30)
    print(f"SUKCES! Plik wyczyszczony.")
    print(f"Oryginalna liczba wierszy: {total_original}")
    print(f"Wiersze gotowe do SQL: {total_cleaned}")
    print(f"Usunięto 'śmieci': {total_original - total_cleaned}")
    print(f"Plik wyjściowy: {PATH_CLEANED_OUT}")

if __name__ == "__main__":
    wyczysc_plik_do_sql()