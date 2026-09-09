import pandas as pd
import numpy as np
import time
import os
import matplotlib.pyplot as plt
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler, MinMaxScaler    # Narzędzie do standaryzacji
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

# --- KONFIGURACJA ŚCIEŻEK I RYGORU SANITARNEGO ---
PATH_INPUT = r"D:\%PRACA_MAGISTERSKA\data\processed\ml_dataset_podejscie_A.parquet"
PATH_REPORT_OUT = r"D:\%PRACA_MAGISTERSKA\results\reports\linear_report.txt"
PATH_PRED_OUT = r"D:\%PRACA_MAGISTERSKA\results\models\linear_predictions.csv"
PATH_FIG_OUT = r"D:\%PRACA_MAGISTERSKA\results\figures\linear_predictions_plot.png"

SPLIT_RING = 225  # Próg podziału na trening i test

def run_linear_pipeline():
    print("="*60)
    print("   ARCHITEKTURA 1: REGRESJA LINIOWA NA DANYCH STANDARYZOWANYCH")
    print("="*60)
    
    # 1. Wczytanie danych i podział chronologiczny
    df = pd.read_parquet(PATH_INPUT)
    
    X = df.drop(columns=['ring', 'D_Vloss'])
    y = df['D_Vloss']
    
    train_mask = df['ring'] <= SPLIT_RING
    test_mask = df['ring'] > SPLIT_RING
    
    X_train_raw = X[train_mask]
    X_test_raw = X[test_mask]
    y_train = y[train_mask]
    y_test = y[test_mask]
    
    rings_all = df['ring'].values
    rings_train = df.loc[train_mask, 'ring'].values
    rings_test = df.loc[test_mask, 'ring'].values
    feature_names = X.columns.tolist()
    
    print(f"-> Dane wczytane. Trening (Ring <= {SPLIT_RING}): {len(X_train_raw)} | Test: {len(X_test_raw)}")
    
    # --- BEZPIECZNA STANDARYZACJA (Z-SCORE) ---
    print("-> Przeprowadzam standaryzację cech wejściowych (X)...")
    scaler = StandardScaler()
    # scaler = MinMaxScaler()
    
    # Fit i transform TYLKO na treningu, na teście TYLKO transform (brak wycieku danych!)
    X_train_scaled = scaler.fit_transform(X_train_raw)
    X_test_scaled = scaler.transform(X_test_raw)
    
    # Konwersja z powrotem na DataFrame, aby zachować nazwy kolumn do ekstrakcji wag
    X_train = pd.DataFrame(X_train_scaled, columns=feature_names)
    X_test = pd.DataFrame(X_test_scaled, columns=feature_names)
    
    # 2. Inicjalizacja i trening modelu
    model = LinearRegression()
    
    print("-> Estymacja parametrów modelu za pomocą Metody Najmniejszych Kwadratów (OLS)...")
    start_fit = time.perf_counter()
    model.fit(X_train, y_train)
    end_fit = time.perf_counter()
    final_fit_time = end_fit - start_fit
    
    # --- EKSTRAKCJA ZSTANDARYZOWANYCH WAG ---
    weights = model.coef_
    intercept = model.intercept_
    
    df_weights = pd.DataFrame({
        'Parametr (Cecha X)': feature_names,
        'Współczynnik standaryzowany (Beta)': weights
    })
    df_weights['Abs_Beta'] = df_weights['Współczynnik standaryzowany (Beta)'].abs()
    df_weights = df_weights.sort_values(by='Abs_Beta', ascending=False).drop(columns=['Abs_Beta'])
    
    # 3. Generowanie predykcji
    y_pred_train = model.predict(X_train)
    y_pred_test = model.predict(X_test)
    
    # Metryki (RMAE jako stosunek MAE do średniej wartości rzeczywistej, wyrażony w %)
    mae_train = mean_absolute_error(y_train, y_pred_train)
    mae_test = mean_absolute_error(y_test, y_pred_test)
    rmse_train = np.sqrt(mean_squared_error(y_train, y_pred_train))
    rmse_test = np.sqrt(mean_squared_error(y_test, y_pred_test))
    
    # Obliczanie RMAE
    rmae_train = (mae_train / np.mean(np.abs(y_train))) * 100
    rmae_test = (mae_test / np.mean(np.abs(y_test))) * 100
    
    r2_train = r2_score(y_train, y_pred_train)
    r2_test = r2_score(y_test, y_pred_test)
    
    # 4. Zapis wyników
    os.makedirs(os.path.dirname(PATH_PRED_OUT), exist_ok=True)
    df_pred = pd.DataFrame({
        'ring': rings_test,
        'D_Vloss_real': y_test.values,
        'D_Vloss_pred': y_pred_test
    })
    df_pred.to_csv(PATH_PRED_OUT, index=False)
    
    # 5. GENEROWANIE KOMPLEKSOWEGO WYKRESU
    os.makedirs(os.path.dirname(PATH_FIG_OUT), exist_ok=True)
    plt.figure(figsize=(15, 6))
    
    plt.plot(rings_all, df['D_Vloss'], color='gray', linestyle='-', linewidth=1, alpha=0.3)
    plt.scatter(rings_all, df['D_Vloss'], color='black', marker='o', s=15, alpha=0.6, label='Wartość rzeczywista (Kriging)')
    plt.scatter(rings_train, y_pred_train, color='royalblue', marker='x', s=25, alpha=0.8, label='Predykcja - Zbiór Treningowy')
    plt.scatter(rings_test, y_pred_test, color='crimson', marker='*', s=40, alpha=0.9, label='Predykcja - Zbiór Testowy')
    plt.axvline(x=SPLIT_RING, color='darkgreen', linestyle='--', linewidth=2.5, label=f'Granica podziału (Ring {SPLIT_RING})')
    
    y_max_plot = df['D_Vloss'].max() * 1.05
    plt.text(110, y_max_plot * 0.9, 'STREFA UCZENIA MODELU\n(Ringi 1-225)', 
             color='darkgreen', fontsize=10, fontweight='bold', ha='center',
             bbox=dict(facecolor='white', alpha=0.8, edgecolor='none'))
    
    plt.text(255, y_max_plot * 0.9, 'STREFA TESTOWA\n(Ringi 226-285)', 
             color='crimson', fontsize=10, fontweight='bold', ha='center',
             bbox=dict(facecolor='white', alpha=0.8, edgecolor='none'))
    
    plt.title(f"Wyniki predykcji ubytku objętości gruntu - Model Baseline", fontsize=12, pad=15)
    plt.xlabel("Numer ringu", fontsize=11)
    plt.ylabel("Zmienna celu: V_loss [%]", fontsize=11)
    
    plt.xlim(0, df['ring'].max() + 5)
    plt.ylim(-0.05, y_max_plot)
    plt.grid(True, linestyle=':', alpha=0.5)
    plt.legend(loc='lower left', frameon=True, shadow=True)
    
    plt.savefig(PATH_FIG_OUT, bbox_inches='tight', dpi=300)
    plt.close()
    print(f"-> Zapisano zaktualizowany wykres: {PATH_FIG_OUT}")
    
    # 6. Zapis raportu tekstowego do pliku
    os.makedirs(os.path.dirname(PATH_REPORT_OUT), exist_ok=True)
    with open(PATH_REPORT_OUT, 'w') as f:
        f.write("=== RAPORT METODOLOGICZNY ML - REGRESJA LINIOWA (STANDARYZOWANA) ===\n")
        f.write(f"Data wygenerowania raportu: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("-" * 50 + "\n")
        f.write(f"Czas treningu finalnego (Final Fit Time): {final_fit_time:.4f} sekundy\n")
        f.write("-" * 50 + "\n")
        f.write(f"WYRAZ WOLNY (BIAS / INTERCEPT b): {intercept:.4f} %\n\n")
        f.write("ESTYMOWANE WSPÓŁCZYNNIKI STANDARYZOWANE (BETA):\n")
        f.write(df_weights.to_string(index=False) + "\n")
        f.write("-" * 50 + "\n")
        f.write("METRYKI BŁĘDU:\n")
        f.write(f"  [TRAIN] MAE:  {mae_train:.4f} %\n")
        f.write(f"  [TEST]  MAE:  {mae_test:.4f} %\n")
        f.write(f"  [TRAIN] RMSE: {rmse_train:.4f} %\n")
        f.write(f"  [TEST]  RMSE: {rmse_test:.4f} %\n")
        f.write(f"  [TRAIN] RMAE: {rmae_train:.4f} %\n")
        f.write(f"  [TEST]  RMAE: {rmae_test:.4f} %\n")
        f.write(f"  [TRAIN] R2:   {r2_train:.4f}\n")
        f.write(f"  [TEST]  R2:   {r2_test:.4f}\n")
    print(f"-> Zapisano raport tekstowy do pliku: {PATH_REPORT_OUT}")
    
    # 7. WYŚWIETLENIE RAPORTU W TERMINALU
    print("\n" + "#"*55)
    print("   RAPORT KOŃCOWY W KONSOLI (MNK BASELINE - STANDARYZOWANY)")
    print("#"*55)
    print(f"Czas fitu: {final_fit_time:.4f}s")
    print(f"Wyraz wolny (Intercept b): {intercept:.4f} %")
    print("\nWyestymowane współczynniki standaryzowane Beta:")
    print(df_weights.to_string(index=False))
    print("\n" + "-"*55)
    print(f"Trening -> MAE: {mae_train:.3f}% | RMSE: {rmse_train:.3f}% | RMAE: {rmae_train:.1f}% | R2: {r2_train:.3f}")
    print(f"Test    -> MAE: {mae_test:.3f}% | RMSE: {rmse_test:.3f}% | RMAE: {rmae_test:.1f}% | R2: {r2_test:.3f}")
    print("#"*55 + "\n")

if __name__ == "__main__":
    run_linear_pipeline()