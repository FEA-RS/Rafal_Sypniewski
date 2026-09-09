import pandas as pd
import numpy as np
import os

# --- KONFIGURACJA ŚCIEŻEK ---
PATH_TBM = r"D:\%PRACA_MAGISTERSKA\data\interim\tbm_features_ring.parquet"
PATH_TARGET = r"D:\%PRACA_MAGISTERSKA\data\interim\raport_Metoda_D_Kriging.parquet"
#PATH_TARGET = r"D:\%PRACA_MAGISTERSKA\data\interim\raport_Metoda_B_Calka.parquet"
PATH_OUTPUT = r"D:\%PRACA_MAGISTERSKA\data\processed\ml_dataset_podejscie_B.parquet"
#PATH_OUTPUT = r"D:\%PRACA_MAGISTERSKA\data\processed\ml_dataset_podejscie_A.parquet"

# Próg korelacji, powyżej którego uznajemy cechy za "bliźniaki"
CORR_THRESHOLD = 0.85

def diagnoza_i_feature_engineering():
    print("="*60)
    print("   URUCHAMIAM DIAGNOSTYKĘ I FUZJĘ DANYCH (PODEJŚCIE A)")
    print("="*60)
    
    # 1. Wczytanie danych
    if not os.path.exists(PATH_TBM) or not os.path.exists(PATH_TARGET):
        print("[BŁĄD] Nie znaleziono plików wejściowych! Sprawdź ścieżki.")
        return
        
    df_tbm = pd.read_parquet(PATH_TBM)
    df_target = pd.read_parquet(PATH_TARGET)
    
    # Czyszczenie TBM z metadanych przestrzenno-czasowych
    metadane = ['timestamp', 'latitude', 'longitude']
    df_tbm_clean = df_tbm.drop(columns=metadane, errors='ignore')
    
    # Fuzja po ringu (tylko V_loss!)
    df_target_clean = df_target[['ring', 'D_Vloss']]
    df = pd.merge(df_tbm_clean, df_target_clean, on='ring', how='inner')
    df = df.sort_values('ring').reset_index(drop=True)
    
    print(f"-> Pomyślnie połączono bazy. Liczba ringów: {len(df)}")
    
    # 2. Analiza korelacji (Serce Podejścia A)
    features_x = df.drop(columns=['ring', 'D_Vloss'])
    corr_matrix = features_x.corr(method='spearman').abs()
    
    # Wyciągamy pary o wysokiej korelacji (tylko trójkąt górny, żeby nie dublować A-B i B-A)
    upper_tri = corr_matrix.where(np.triu(np.ones(corr_matrix.shape), k=1).astype(bool))
    
    print(f"\n[1] ANALIZA KORELACJI SPEARMANA (Próg R > {CORR_THRESHOLD}):")
    pary_do_usuniecia = []
    
    for col in upper_tri.columns:
        skorelowane_z = upper_tri.index[upper_tri[col] > CORR_THRESHOLD].tolist()
        if skorelowane_z:
            print(f"   - Cecha '{col}' jest krytycznie skorelowana z: {skorelowane_z}")
            # Logika selekcji: domyślnie sugerujemy usunięcie rozstępu (range) na rzecz średniej (avg)
            if 'range' in col:
                pary_do_usuniecia.append(col)
            else:
                # Jeśli to dwie średnie, usuwamy tę podaną jako 'col'
                pary_do_usuniecia.append(col)
                
    pary_do_usuniecia = list(set(pary_do_usuniecia))
    
    # 3. Analiza rzadkich warstw geologicznych
    print("\n[2] ANALIZA WARSTW GEOLOGICZNYCH (SPARSITY):")
    soil_cols = [c for c in df.columns if c.startswith('soil_')]
    rzadkie_warstwy = []
    
    for col in soil_cols:
        procent_wystepowania = (df[col] > 0).sum() / len(df)
        print(f"   - {col}: obecna na {df[col].astype(bool).sum()} ringach ({procent_wystepowania:.1%})")
        if procent_wystepowania < 0.05: # Mniej niż 5% ringów
            rzadkie_warstwy.append(col)
            
    # 4. Decyzja i generowanie raportu końcowego
    print("\n" + "="*50)
    print("   PODSUMOWANIE ANALIZY - CO SUGERUJE MATEMATYKA?")
    print("="*50)
    print(f"Wszystkich cech na starcie: {len(features_x.columns)}")
    print(f"Sugerowane cechy maszyny do USUNIĘCIA (R > {CORR_THRESHOLD}): {pary_do_usuniecia}")
    print(f"Sugerowane rzadkie geologie do SCALENIA (< 5% ringów): {rzadkie_warstwy}")
    
    # Wykonujemy cięcie dla wersji A
    df_a = df.drop(columns=pary_do_usuniecia)
    if rzadkie_warstwy:
        df_a['soil_OTHER'] = df_a[rzadkie_warstwy].sum(axis=1)
        df_a = df_a.drop(columns=rzadkie_warstwy)
        
    print(f"\n[WYNIK] Po odchudzeniu w zbiorze A zostaje: {len(df_a.drop(columns=['ring', 'D_Vloss']).columns)} cech.")
    print(f"Ostateczna lista cech (Podejście A):\n{list(df_a.drop(columns=['ring', 'D_Vloss']).columns)}")
    print("="*50)
    
    # Zapisujemy zbiór danych dla Podejścia A
    os.makedirs(os.path.dirname(PATH_OUTPUT), exist_ok=True)
    df_a.to_parquet(PATH_OUTPUT, index=False)
    print(f"Zapisano czysty zbiór danych (Podejście A) do: {PATH_OUTPUT}\n")

if __name__ == "__main__":
    diagnoza_i_feature_engineering()