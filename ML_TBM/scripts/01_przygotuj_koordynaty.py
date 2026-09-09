import os
import pandas as pd
from pyproj import Transformer
from datetime import datetime

# ==========================================
# 1. KONFIGURACJA ŚCIEŻEK
# ==========================================
SCIEZKA_WEJSCIOWA = r"D:\%PRACA_MAGISTERSKA\data\raw\koordynaty\coordinate_copy.txt"
SCIEZKA_WYJSCIOWA = r"D:\%PRACA_MAGISTERSKA\data\interim\sensors_metadata.csv"
SCIEZKA_RAPORTU = r"D:\%PRACA_MAGISTERSKA\results\reports\ETL_raport_koordynaty.txt"

# Inicjalizacja konwertera (PUWG 2000 strefa 6 -> WGS84)
transformer = Transformer.from_crs("EPSG:2177", "EPSG:4326", always_xy=False)

# ==========================================
# 2. FUNKCJA PRZETWARZAJĄCA
# ==========================================

def przygotuj_czujniki():
    print("Rozpoczynam odczyt i konwersję koordynatów...")
    
# Wczytanie danych z TXT
    df = pd.read_csv(
        SCIEZKA_WEJSCIOWA, 
        sep='\t', 
        header=None, 
        names=['sensor_id', 'X', 'Y', 'altitude'],
        usecols=[0, 1, 2, 3],       
        on_bad_lines='warn',        
        engine='python'             
    )
    
    # --- TA LINIA NAPRAWI TWÓJ BŁĄD ---
    # Usuwamy duplikaty: jeśli sensor_id się powtarza, zostawiamy tylko pierwszy wpis
    df.drop_duplicates(subset=['sensor_id'], keep='first', inplace=True)
    # ---------------------------------
    
    poczatkowa_liczba = len(df)
    # Funkcja do konwersji
    def konwertuj_wiersz(row):
        if row['X'] == 0 and row['Y'] == 0:
            return pd.Series({
                'latitude': 0.0, 
                'longitude': 0.0,
                'description': 'DO_WERYFIKACJI_BRAK_WSPOLRZEDNYCH'
            })
            
        lat, lon = transformer.transform(row['X'], row['Y'])
        return pd.Series({
            'latitude': round(lat, 6), 
            'longitude': round(lon, 6),
            'description': None
        })

    # Aplikujemy konwersję
    df[['latitude', 'longitude', 'description']] = df.apply(konwertuj_wiersz, axis=1)
    
    # Liczymy statystyki do raportu
    czujniki_bez_wspolrzednych = df[df['description'] == 'DO_WERYFIKACJI_BRAK_WSPOLRZEDNYCH']
    liczba_blednych = len(czujniki_bez_wspolrzednych)
    
    # Zapis danych do CSV
    gotowa_tabela = df[['sensor_id', 'latitude', 'longitude', 'altitude', 'description']]
    gotowa_tabela.to_csv(SCIEZKA_WYJSCIOWA, index=False)
    
    # ==========================================
    # 3. GENEROWANIE RAPORTU TEKSTOWEGO
    # ==========================================
    with open(SCIEZKA_RAPORTU, 'w', encoding='utf-8') as plik:
        plik.write(f"--- RAPORT Z PRZETWARZANIA KOORDYNATÓW ---\n")
        plik.write(f"Data wygenerowania: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        plik.write(f"Wczytano czujników z pliku surowego: {poczatkowa_liczba}\n")
        plik.write(f"Zapisano czujników do pliku końcowego: {len(gotowa_tabela)}\n")
        plik.write(f"Znaleziono czujników z zerowymi współrzędnymi (0,0): {liczba_blednych}\n\n")
        
        if liczba_blednych > 0:
            plik.write("Lista czujników bez współrzędnych:\n")
            for id_czujnika in czujniki_bez_wspolrzednych['sensor_id']:
                plik.write(f" - {id_czujnika}\n")
    
    print(f"Sukces! Skonwertowano {len(gotowa_tabela)} czujników.")
    print(f"Wygenerowano raport ETL: {SCIEZKA_RAPORTU}")

# ==========================================
# WYWOŁANIE
# ==========================================
if __name__ == "__main__":
    przygotuj_czujniki()