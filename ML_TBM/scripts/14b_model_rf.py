import pandas as pd
import numpy as np
import time
import os
import matplotlib.pyplot as plt
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import TimeSeriesSplit, GridSearchCV

# --- KONFIGURACJA ŚCIEŻEK ---
PATH_INPUT = r"D:\%PRACA_MAGISTERSKA\data\processed\ml_dataset_podejscie_A.parquet"
PATH_REPORT_OUT = r"D:\%PRACA_MAGISTERSKA\results\reports\rf_report.txt"
PATH_PRED_OUT = r"D:\%PRACA_MAGISTERSKA\results\models\rf_predictions.csv"
PATH_FIG_OUT = r"D:\%PRACA_MAGISTERSKA\results\figures\rf_predictions_plot.png"

SPLIT_RING = 225

def run_rf_pipeline():
    print("="*60)
    print("   ARCHITEKTURA 2: RANDOM FOREST (LAS LOSOWY) - GRIND")
    print("="*60)
    
    # 1. Wczytanie i sortowanie danych
    df = pd.read_parquet(PATH_INPUT)
    df = df.sort_values(by='ring').reset_index(drop=True)
    
    feature_cols = [c for c in df.columns if c not in ['ring', 'D_Vloss']]
    X = df[feature_cols].values
    y = df['D_Vloss'].values
    rings = df['ring'].values
    
    # 2. Chronologiczny podział na Trening i Test
    train_mask = rings <= SPLIT_RING
    test_mask = rings > SPLIT_RING
    
    X_train, y_train = X[train_mask], y[train_mask]
    X_test, y_test = X[test_mask], y[test_mask]
    rings_train, rings_test = rings[train_mask], rings[test_mask]
    
    # 3. Standaryzacja
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    
    # 4. DEFINICJA PRZESTRZENI HIPERPARAMETRÓW
    rf_base = RandomForestRegressor(random_state=42)
    
    param_grid = {
        'n_estimators': [70, 80, 90, 100],
        'max_depth': [6, 7, 8, 9, 10],
        'min_samples_split': [2, 3, 4],
        'max_samples': [0.5, 0.7, 0.9],
        'ccp_alpha': [0.0, 0.001, 0.005]
    }
    
    tscv = TimeSeriesSplit(n_splits=5)
    
    print("-> Rozpoczynam tuning (GridSearchCV)... To chwilę potrwa.")
    start_time = time.perf_counter()
    
    grid_search = GridSearchCV(
        estimator=rf_base, 
        param_grid=param_grid, 
        cv=tscv, 
        scoring='neg_root_mean_squared_error',
        n_jobs=-1,
        verbose=1
    )
    
    grid_search.fit(X_train_scaled, y_train)
    end_time_grid = time.perf_counter()
    best_rf = grid_search.best_estimator_
    print(f"-> Znaleziono optymalne parametry:\n{grid_search.best_params_}")
    
    # 5. PREDYKCJA NA NAJLEPSZYM MODELU
    y_pred_train = best_rf.predict(X_train_scaled)
    y_pred_test = best_rf.predict(X_test_scaled)
    
    # 6. OBLICZANIE METRYK (w tym RMAE)
    mae_train = mean_absolute_error(y_train, y_pred_train)
    mae_test = mean_absolute_error(y_test, y_pred_test)
    rmse_train = np.sqrt(mean_squared_error(y_train, y_pred_train))
    rmse_test = np.sqrt(mean_squared_error(y_test, y_pred_test))
    
    # Obliczanie RMAE
    rmae_train = (mae_train / np.mean(np.abs(y_train))) * 100
    rmae_test = (mae_test / np.mean(np.abs(y_test))) * 100
    
    r2_train = r2_score(y_train, y_pred_train)
    r2_test = r2_score(y_test, y_pred_test)
    
    # 7. GENEROWANIE WYKRESU
    os.makedirs(os.path.dirname(PATH_FIG_OUT), exist_ok=True)
    plt.figure(figsize=(15, 6))
    plt.plot(rings, y, color='gray', linestyle='-', linewidth=1, alpha=0.3)
    plt.scatter(rings, y, color='black', marker='o', s=15, alpha=0.6, label='Wartość rzeczywista (Kriging)')
    plt.scatter(rings_train, y_pred_train, color='royalblue', marker='x', s=25, alpha=0.8, label='Predykcja - Trening')
    plt.scatter(rings_test, y_pred_test, color='crimson', marker='*', s=40, alpha=0.9, label='Predykcja - Test')
    plt.axvline(x=SPLIT_RING, color='darkgreen', linestyle='--', linewidth=2.5, label=f'Granica podziału ({SPLIT_RING})')
    
    y_max_plot = max(df['D_Vloss'].max(), max(y_pred_train), max(y_pred_test)) * 1.05
    plt.text(110, y_max_plot * 0.9, 'STREFA UCZENIA MODELU\n(Ringi 1-225)', color='darkgreen', fontsize=10, fontweight='bold', ha='center', bbox=dict(facecolor='white', alpha=0.8, edgecolor='none'))
    plt.text(255, y_max_plot * 0.9, 'STREFA TESTOWA\n(Ringi 226-285)', color='crimson', fontsize=10, fontweight='bold', ha='center', bbox=dict(facecolor='white', alpha=0.8, edgecolor='none'))
    
    plt.title(f"Wyniki predykcji ubytku gruntu - Random Forest", fontsize=12, pad=15)
    plt.xlabel("Numer ringu", fontsize=11)
    plt.ylabel("Zmienna celu: V_loss [%]", fontsize=11)
    plt.xlim(0, df['ring'].max() + 5)
    plt.ylim(-0.05, max(0.35, y_max_plot))
    plt.grid(True, linestyle=':', alpha=0.5)
    plt.legend(loc='lower left', frameon=True, shadow=True)
    plt.savefig(PATH_FIG_OUT, bbox_inches='tight', dpi=300)
    plt.close()
    
    # 8. RAPORT W KONSOLI
# 8. RAPORT W KONSOLI
    print("\n" + "#"*55)
    print("   RAPORT KOŃCOWY W KONSOLI (Random Forest - GRIND)")
    print("#"*55)
    print(f"Czas GridSearch: {end_time_grid - start_time:.2f}s")
    print(f"Wybrane parametry: {grid_search.best_params_}")
    print("Wbudowany ranking istotności cech (MDI Gini):\n")
    print(f"{'Parametr (Cecha X)':>20}  Znaczenie Gini")
    
    # --- POBIERANIE I SORTOWANIE ISTOTNOŚCI CECH ---
    importances = best_rf.feature_importances_
    feature_importance_df = pd.DataFrame({
        'Feature': feature_cols,
        'Importance': importances
    }).sort_values(by='Importance', ascending=False)

    # --- DRUKOWANIE ROZPISKI ---
    for _, row in feature_importance_df.iterrows():
        print(f"{row['Feature']:>20}        {row['Importance']:.6f}")
    
    print("-" * 55)
    print(f"Trening -> MAE: {mae_train:.3f}% | RMSE: {rmse_train:.3f}% | RMAE: {rmae_train:.1f}% | R2: {r2_train:.3f}")
    print(f"Test    -> MAE: {mae_test:.3f}% | RMSE: {rmse_test:.3f}% | RMAE: {rmae_test:.1f}% | R2: {r2_test:.3f}")
    print("#"*55 + "\n")

if __name__ == "__main__":
    run_rf_pipeline()