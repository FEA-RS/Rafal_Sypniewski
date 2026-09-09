import pandas as pd
import os
import re

# Ścieżki plików
PATH_READINGS = r"D:\%PRACA_MAGISTERSKA\data\interim\new_readings_to_import.csv"
PATH_META_IN = r"D:\%PRACA_MAGISTERSKA\data\interim\sensors_metadata.csv"
PATH_META_OUT = r"D:\%PRACA_MAGISTERSKA\data\interim\sensors_metadata_v2.csv"

def get_base_id(sensor_id):
    """Wyciąga rdzeń nazwy do szukania podobnych czujników"""
    # Usuwa końcówki: _R, _B, _BX, _BY, _BZ, _T, _M1, _M2
    clean = re.sub(r'(_?[R|B|BX|BY|BZ|T|M1|M2])$', '', str(sensor_id))
    # Usuwa ewentualną ostatnią literę (np. CM0010_01B -> CM0010_01)
    return re.sub(r'[A-Z]$', '', clean).strip('_')

def wykonaj_synchronizacje():
    print("Rozpoczynam rygorystyczną synchronizację metadanych...")
    
    # Wczytujemy dane
    df_readings = pd.read_csv(PATH_READINGS, usecols=['sensor_id'])
    df_meta = pd.read_csv(PATH_META_IN)
    
    # Unikalne czujniki z odczytów
    all_readings_ids = df_readings['sensor_id'].unique()
    existing_meta_ids = set(df_meta['sensor_id'].unique())
    
    new_rows = []
    ignored_count = 0
    
    for sid in all_readings_ids:
        if sid in existing_meta_ids:
            continue
            
        # Próba odzyskania współrzędnych (Fuzzy Matching)
        base = get_base_id(sid)
        match = df_meta[df_meta['sensor_id'].str.contains(base, na=False)]
        
        if not match.empty:
            # ODZYSKIWANIE: Kopiujemy koordynaty od znalezionego "rodzica"
            ref = match.iloc[0]
            new_rows.append({
                'sensor_id': sid,
                'latitude': ref['latitude'],
                'longitude': ref['longitude'],
                'altitude': ref['altitude'],
                'description': f"Automatyczne dopasowanie na podstawie {ref['sensor_id']}"
            })
        else:
            # POMIJANIE: Nie dodajemy wiersza z zerami - ten czujnik zostanie usunięty z importu
            ignored_count += 1
            
    # Łączymy stare z nowymi (tylko tymi odzyskanymi)
    df_final = pd.concat([df_meta, pd.DataFrame(new_rows)], ignore_index=True)
    df_final.to_csv(PATH_META_OUT, index=False)
    
    print("-" * 30)
    print(f"ZAKOŃCZONO SYNCHRONIZACJĘ")
    print(f"Czujniki w nowym metadanych: {len(df_final)}")
    print(f"Uratowano przez dopasowanie: {len(new_rows)}")
    print(f"Definitywnie usunięto (brak lokalizacji): {ignored_count}")
    print(f"Plik wynikowy: {PATH_META_OUT}")

if __name__ == "__main__":
    wykonaj_synchronizacje()