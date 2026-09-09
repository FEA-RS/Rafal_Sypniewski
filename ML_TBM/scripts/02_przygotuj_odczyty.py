import os
import pandas as pd
from datetime import datetime
import re

# ==========================================
# 1. KONFIGURACJA
# ==========================================
FOLDER_WEJSCIOWY = r"D:\%PRACA_MAGISTERSKA\data\raw\odczyty_czujnikow"
PLIK_MASTER = r"D:\%PRACA_MAGISTERSKA\data\interim\master_readings.csv"
PLIK_DO_IMPORTU = r"D:\%PRACA_MAGISTERSKA\data\interim\new_readings_to_import.csv"
SCIEZKA_RAPORTU = r"D:\%PRACA_MAGISTERSKA\results\reports\ETL_raport_odczyty.txt"

KOLUMNY_SQL = ['timestamp', 'sensor_id', 'settlement_value', 'reading_type', 'measurement_desc']

MAPA_OPISOW = {
    'R': 'Odczyt na reperze',
    'BZ': 'Przemieszczenie pionowe (Oś Z)',
    'BX': 'Przemieszczenie poziome (Oś X)',
    'BY': 'Przemieszczenie poziome (Oś Y)'
}

def clean_sensor_id(s_name):
    """Absolutne czyszczenie ID do formatu akceptowanego przez Twoją bazę"""
    s_name = s_name.strip().upper()
    
    # 1. Jeśli kończy się na BX, BY, BZ -> ucinamy ostatnią literę (zostaje B)
    s_name = re.sub(r'([XYZ])$', '', s_name)
    
    # 2. UJEDNOLICANIE: Usuwamy wstawki typu _A_, _D_ (np. CM0030_A_04B -> CM0030_04B)
    # Robimy to tylko jeśli takie wzorce występują w Twoich błędach
    s_name = s_name.replace('_A_', '_').replace('_D_', '_')
    
    return s_name

def przygotuj_odczyty():
    print("Odpalam czyszczenie danych... Pamiętaj o usunięciu starego master_readings.csv!")
    nowe_dane_lista = []
    stat_arkusze = 0

    for plik in os.listdir(FOLDER_WEJSCIOWY):
        if plik.endswith(".xlsx") and not plik.startswith("~$"):
            sciezka = os.path.join(FOLDER_WEJSCIOWY, plik)
            nazwa_low = plik.lower()
            typ_pomiaru = "Z" if "osi z" in nazwa_low else "XY" if "osiach x i y" in nazwa_low else "UNKNOWN"
            
            try:
                excel_file = pd.ExcelFile(sciezka)
                for sheet_name in excel_file.sheet_names:
                    orig_name = str(sheet_name).strip()
                    
                    # Filtrujemy tylko to co chciałeś: R, BZ, BX, BY
                    opis_pomiaru = None
                    for koncowka, opis in MAPA_OPISOW.items():
                        if orig_name.endswith(koncowka):
                            opis_pomiaru = opis
                            break
                    
                    if not opis_pomiaru:
                        continue
                    
                    stat_arkusze += 1
                    df = pd.read_excel(sciezka, sheet_name=sheet_name, usecols=[0, 1], 
                                     names=['timestamp', 'settlement_value'], header=0)
                    
                    df['sensor_id'] = clean_sensor_id(orig_name)
                    df['reading_type'] = typ_pomiaru
                    df['measurement_desc'] = opis_pomiaru 
                    df['timestamp'] = pd.to_datetime(df['timestamp'], dayfirst=True, errors='coerce')
                    df.dropna(subset=['timestamp', 'settlement_value'], inplace=True)
                    
                    nowe_dane_lista.append(df[KOLUMNY_SQL])
            except Exception as e:
                print(f"Błąd w pliku {plik}: {e}")

    if not nowe_dane_lista: return

    df_final = pd.concat(nowe_dane_lista, ignore_index=True)
    df_final.drop_duplicates(subset=['sensor_id', 'timestamp', 'measurement_desc'], inplace=True)
    
    # Zapisujemy wszystko jako NOWY master i NOWY import
    df_final.sort_values(by=['sensor_id', 'timestamp'], inplace=True)
    df_final.to_csv(PLIK_MASTER, index=False)
    df_final.to_csv(PLIK_DO_IMPORTU, index=False)
    
    print(f"Sukces! Przetworzono {stat_arkusze} arkuszy. Wygenerowano {len(df_final)} rekordów.")

if __name__ == "__main__":
    przygotuj_odczyty()