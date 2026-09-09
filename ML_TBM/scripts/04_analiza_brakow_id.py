import pandas as pd
import os
import re

# Konfiguracja ścieżek
PATH_READINGS = r"D:\%PRACA_MAGISTERSKA\data\interim\new_readings_to_import.csv"
PATH_META = r"D:\%PRACA_MAGISTERSKA\data\interim\sensors_metadata.csv"
PATH_OUTPUT_REPORT = r"D:\%PRACA_MAGISTERSKA\results\reports\raport_naprawczy_id.txt"

def get_base_id(sensor_id):
    """Wyciąga rdzeń nazwy, usuwając końcówki typowe dla pomiarów (R, B, BX itd.)"""
    # Usuwa końcówki: _R, _B, _BX, _BY, _BZ, _T, _M1, _M2 oraz litery na samym końcu
    clean = re.sub(r'(_?[R|B|BX|BY|BZ|T|M1|M2])$', '', str(sensor_id))
    # Usuwa dodatkowe litery na końcu jeśli zostały (np. CM0010_01B -> CM0010_01)
    clean = re.sub(r'[A-Z]$', '', clean)
    return clean.strip('_')

def analizuj_mozliwosc_naprawy():
    if not os.path.exists(PATH_READINGS) or not os.path.exists(PATH_META):
        print("BŁĄD: Brak plików źródłowych w folderze interim.")
        return

    # Wczytywanie danych
    df_readings = pd.read_csv(PATH_READINGS, usecols=['sensor_id', 'measurement_desc'])
    df_meta = pd.read_csv(PATH_META, usecols=['sensor_id'])

    readings_ids = set(df_readings['sensor_id'].unique())
    meta_ids = set(df_meta['sensor_id'].unique())

    missing_ids = readings_ids - meta_ids
    
    do_odzyskania = []
    bez_szans = []

    for mid in missing_ids:
        base = get_base_id(mid)
        # Szukamy czy w metadanych istnieje cokolwiek co zawiera ten rdzeń
        matches = [m for m in meta_ids if base in m]
        
        count = len(df_readings[df_readings['sensor_id'] == mid])
        
        if matches:
            do_odzyskania.append({
                'id': mid,
                'base_found': matches[0],
                'rows': count
            })
        else:
            bez_szans.append({
                'id': mid,
                'rows': count
            })

    # Generowanie raportu
    total_rows = len(df_readings)
    rows_to_recover = sum(item['rows'] for item in do_odzyskania)
    rows_lost = sum(item['rows'] for item in bez_szans)

    with open(PATH_OUTPUT_REPORT, 'w', encoding='utf-8') as f:
        f.write("SZCZEGÓŁOWY RAPORT INTEGRALNOŚCI I MOŻLIWOŚCI NAPRAWY\n")
        f.write("="*60 + "\n")
        f.write(f"Łączna liczba rekordów w pliku: {total_rows}\n")
        f.write(f"Rekordy poprawne (już w bazie): {total_rows - rows_to_recover - rows_lost}\n")
        f.write(f"Rekordy MOŻLIWE do odzyskania: {rows_to_recover} ({ (rows_to_recover/total_rows)*100 :.2f}%)\n")
        f.write(f"Rekordy DEFINITYWNIE stracone: {rows_lost} ({ (rows_lost/total_rows)*100 :.2f}%)\n")
        f.write("-" * 60 + "\n\n")

        f.write("1. LISTA DO AUTOMATYCZNEGO DOPISANIA (Istnieje baza w metadanych):\n")
        f.write(f"{'ID CZUJNIKA':<20} | {'ZNALEZIONA BAZA':<20} | {'LICZBA WIERSZY':<15}\n")
        f.write("-" * 60 + "\n")
        for item in sorted(do_odzyskania, key=lambda x: x['rows'], reverse=True):
            f.write(f"{item['id']:<20} | {item['base_found']:<20} | {item['rows']:<15}\n")

        f.write("\n2. LISTA DO POMINIĘCIA (Brak punktu odniesienia w metadanych):\n")
        f.write(f"{'ID CZUJNIKA':<20} | {'LICZBA WIERSZY':<15}\n")
        f.write("-" * 40 + "\n")
        for item in sorted(bez_szans, key=lambda x: x['rows'], reverse=True):
            f.write(f"{item['id']:<20} | {item['rows']:<15}\n")

    print(f"Analiza zakończona. Raport: {PATH_OUTPUT_REPORT}")

if __name__ == "__main__":
    analizuj_mozliwosc_naprawy()