import pandas as pd
import numpy as np
import os
import matplotlib.pyplot as plt
import seaborn as sns

# --- KONFIGURACJA ŚCIEŻEK ---
PATH_TBM = r"D:\%PRACA_MAGISTERSKA\data\interim\tbm_features_ring.parquet"
#PATH_TARGET = r"D:\%PRACA_MAGISTERSKA\data\interim\raport_Metoda_D_Kriging.parquet"
PATH_TARGET = r"D:\%PRACA_MAGISTERSKA\data\interim\raport_Metoda_B_Calka.parquet"
PATH_OUTPUT = r"D:\%PRACA_MAGISTERSKA\data\processed\ml_dataset_podejscie_A.parquet"
PATH_PLOT = r"D:\%PRACA_MAGISTERSKA\results\figures\niecki_ring\macierz_korelacji_trojkat.png"
PATH_REPORT = r"D:\%PRACA_MAGISTERSKA\results\reports\raport_analiza_cech.txt"  # DODANE

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
    
    # Wizualizacja górnego trójkąta
    print("\n[WIZUALIZACJA] Generowanie mapy ciepła (tylko górny trójkąt)...")
    mask = np.tril(np.ones_like(corr_matrix, dtype=bool), k=0)
    
    plt.figure(figsize=(14, 12))  
    ax = sns.heatmap(
        corr_matrix, 
        mask=mask,             
        cmap='coolwarm',       
        vmin=0, vmax=1,        
        annot=False,           
        linewidths=0.5,        
        cbar_kws={"label": "Współczynnik korelacji Spearmana (abs)"}
    )
    
    ax.collections[0].colorbar.ax.yaxis.label.set_size(20)
    ax.collections[0].colorbar.ax.tick_params(labelsize=18)
    ax.tick_params(axis='both', which='major', labelsize=14)
    plt.title(f"Macierz korelacji Spearmana dla cech TBM (górna część trójkątna)", fontsize=20, pad=15)
    plt.tight_layout()
    
    os.makedirs(os.path.dirname(PATH_PLOT), exist_ok=True)
    plt.savefig(PATH_PLOT, dpi=600)
    print(f"-> Wykres macierzy zapisano do: {PATH_PLOT}")
    #plt.show()  
    
    # Wyciągamy pary o wysokiej korelacji
    upper_tri = corr_matrix.where(np.triu(np.ones(corr_matrix.shape), k=1).astype(bool))
    
    print(f"\n[1] ANALIZA KORELACJI SPEARMANA (Próg R > {CORR_THRESHOLD}):")
    pary_do_usuniecia = []
    szczegoly_korelacji = [] # Pomocnicza lista do raportu
    
    for col in upper_tri.columns:
        skorelowane_z = upper_tri.index[upper_tri[col] > CORR_THRESHOLD].tolist()
        if skorelowane_z:
            komunikat = f"   - Cecha '{col}' jest krytycznie skorelowana z: {skorelowane_z}"
            print(komunikat)
            szczegoly_korelacji.append(komunikat)
            pary_do_usuniecia.append(col)
                
    pary_do_usuniecia = list(set(pary_do_usuniecia))
    
    # 3. Analiza rzadkich warstw geologicznych
    print("\n[2] ANALIZA WARSTW GEOLOGICZNYCH (SPARSITY):")
    soil_cols = [c for c in df.columns if c.startswith('soil_')]
    rzadkie_warstwy = []
    szczegoly_geologii = [] # Pomocnicza lista do raportu
    
    for col in soil_cols:
        procent_wystepowania = (df[col] > 0).sum() / len(df)
        komunikat = f"   - {col}: obecna na {df[col].astype(bool).sum()} ringach ({procent_wystepowania:.1%})"
        print(komunikat)
        szczegoly_geologii.append(komunikat)
        if procent_wystepowania < 0.05:
            rzadkie_warstwy.append(col)
            
    # Wykonujemy cięcie dla wersji A
    df_a = df.drop(columns=pary_do_usuniecia)
    if rzadkie_warstwy:
        df_a['soil_OTHER'] = df_a[rzadkie_warstwy].sum(axis=1)
        df_a = df_a.drop(columns=rzadkie_warstwy)
        
    ostateczne_cechy = list(df_a.drop(columns=['ring', 'D_Vloss']).columns)
    
    # 4. Generowanie raportu końcowego (Konsola + Zapis do pliku)
    print("\n" + "="*50)
    print("   PODSUMOWANIE ANALIZY - CO SUGERUJE MATEMATYKA?")
    print("="*50)
    print(f"Wszystkich cech na starcie: {len(features_x.columns)}")
    print(f"Sugerowane cechy maszyny do USUNIĘCIA (R > {CORR_THRESHOLD}): {pary_do_usuniecia}")
    print(f"Sugerowane rzadkie geologie do SCALENIA (< 5% ringów): {rzadkie_warstwy}")
    print(f"\n[WYNIK] Po odchudzeniu w zbiorze A zostaje: {len(ostateczne_cechy)} cech.")
    print(f"Ostateczna lista cech (Podejście A):\n{ostateczne_cechy}")
    print("="*50)
    
    os.makedirs(os.path.dirname(PATH_REPORT), exist_ok=True)
    with open(PATH_REPORT, "w", encoding="utf-8") as f:
        f.write("==================================================\n")
        f.write("   RAPORT Z DIAGNOSTYKI I SELEKCJI CECH (PODEJŚCIE A)\n")
        f.write("==================================================\n\n")
        f.write(f"Liczba ringów po fuzji baz: {len(df)}\n")
        f.write(f"Liczba cech na starcie: {len(features_x.columns)}\n\n")
        
        f.write(f"[1] WYKRYTE SILNE KORELACJE (R > {CORR_THRESHOLD}):\n")
        for linia in szczegoly_korelacji:
            f.write(linia + "\n")
        f.write(f"--> Usunięte kolumny z powodu korelacji ({len(pary_do_usuniecia)}): {pary_do_usuniecia}\n\n")
        
        f.write("[2] ANALIZA SPARSITY WARSTW GEOLOGICZNYCH:\n")
        for linia in szczegoly_geologii:
            f.write(linia + "\n")
        f.write(f"--> Scalone rzadkie warstwy (<5%): {rzadkie_warstwy}\n\n")
        
        f.write("==================================================\n")
        f.write(f"PODSUMOWANIE: Liczba cech po odchudzeniu: {len(ostateczne_cechy)}\n")
        f.write("==================================================\n")
        f.write("Ostateczna lista cech wejściowych dla modeli ML:\n")
        for cecha in ostateczne_cechy:
            f.write(f" - {cecha}\n")
            
    print(f"Zapisano raport tekstowy do: {PATH_REPORT}")
    
    # Zapisujemy zbiór danych dla Podejścia A
    os.makedirs(os.path.dirname(PATH_OUTPUT), exist_ok=True)
    df_a.to_parquet(PATH_OUTPUT, index=False)
    print(f"Zapisano czysty zbiór danych (Podejście A) do: {PATH_OUTPUT}\n")

if __name__ == "__main__":
    diagnoza_i_feature_engineering()