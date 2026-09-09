import pandas as pd
import numpy as np
import time
import os
import matplotlib.pyplot as plt
from xgboost import XGBRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import GridSearchCV, TimeSeriesSplit
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

# --- KONFIGURACJA ŚCIEŻEK I RYGORU SANITARNEGO ---
PATH_INPUT = r"D:\%PRACA_MAGISTERSKA\data\processed\ml_dataset_podejscie_A.parquet"
PATH_REPORT_OUT = r"D:\%PRACA_MAGISTERSKA\results\reports\xgboost_report.txt"
PATH_PRED_OUT = r"D:\%PRACA_MAGISTERSKA\results\models\xgboost_predictions.csv"
PATH_FIG_OUT = r"D:\%PRACA_MAGISTERSKA\results\figures\xgboost_predictions_plot.png"

SPLIT_RING = 225  # Próg podziału na trening i test

def run_xgboost_pipeline():
    print("="*60)
    print("   ARCHITEKTURA 3: XGBOOST - KLASYCZNY PIPELINE (POPRAWIONY)")
    print("="*60)
    
    # 1. Wczytanie danych i podział chronologiczny
    df = pd.read_parquet(PATH_INPUT)
    
    X = df.drop(columns=['ring', 'D_Vloss'])
    y = df['D_Vloss']
    
    train_mask = df['ring'] <= SPLIT_RING
    test_mask = df['ring'] > SPLIT_RING
    
    X_train_raw, X_test_raw = X[train_mask], X[test_mask]
    y_train, y_test = y[train_mask], y[test_mask]
    
    rings_all = df['ring'].values
    rings_train = df.loc[train_mask, 'ring'].values
    rings_test = df.loc[test_mask, 'ring'].values
    feature_names = X.columns.tolist()
    
    print(f"-> Dane wczytane. Trening (Ring <= {SPLIT_RING}): {len(X_train_raw)} | Test: {len(X_test_raw)}")
    
    # 2. Standaryzacja danych
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train_raw)
    X_test_scaled = scaler.transform(X_test_raw)
    
    X_train = pd.DataFrame(X_train_scaled, columns=feature_names)
    X_test = pd.DataFrame(X_test_scaled, columns=feature_names)
    
    # 3. Definicja stabilnej przestrzeni hiperparametrów
    xgb_base = XGBRegressor(random_state=42, objective='reg:squarederror')
    
    param_grid = {
        'max_depth': [3, 4, 5, 6],
        'min_child_weight': [1, 2, 3],
        'reg_lambda': [1.0, 2.0, 5.0],
        'learning_rate': [0.05, 0.1, 0.2],
        'subsample': [0.7, 0.85, 1.0],
        'colsample_bytree': [0.7, 0.85, 1.0],
        'n_estimators': [100, 150]
    }
    
    # Walidacja 3-foldowa czasowa
    tscv = TimeSeriesSplit(n_splits=3)
    
    # Optymalizacja klasyczna (MSE)
    grid_search = GridSearchCV(
        estimator=xgb_base, 
        param_grid=param_grid, 
        cv=tscv, 
        scoring='neg_mean_squared_error', 
        n_jobs=-1
    )
    
    # 4. Pomiar Czasu 1: Łączna optymalizacja
    print("-> Uruchamiam GridSearchCV (pełna siatka)...")
    start_tuning = time.perf_counter()
    grid_search.fit(X_train, y_train)
    end_tuning = time.perf_counter()
    tuning_time = end_tuning - start_tuning
    
    best_params = grid_search.best_params_
    print(f"   [OK] Najlepsza konfiguracja: {best_params}")
    
    # 5. Pomiar Czasu 2: Ostateczny trening na najlepszych parametrach
    best_xgb = grid_search.best_estimator_
    
    print("-> Trenuję ostateczny model XGBoost...")
    start_fit = time.perf_counter()
    best_xgb.fit(X_train, y_train)
    end_fit = time.perf_counter()
    final_fit_time = end_fit - start_fit
    
    # 6. Generowanie predykcji i metryk
    y_pred_train = best_xgb.predict(X_train)
    y_pred_test = best_xgb.predict(X_test)
    
    mae_train = mean_absolute_error(y_train, y_pred_train)
    mae_test = mean_absolute_error(y_test, y_pred_test)
    rmse_train = np.sqrt(mean_squared_error(y_train, y_pred_train))
    rmse_test = np.sqrt(mean_squared_error(y_test, y_pred_test))
    
    rmae_train = (mae_train / np.mean(np.abs(y_train))) * 100
    rmae_test = (mae_test / np.mean(np.abs(y_test))) * 100
    
    r2_train = r2_score(y_train, y_pred_train)
    r2_test = r2_score(y_test, y_pred_test)
    
    importances = best_xgb.feature_importances_
    df_imp = pd.DataFrame({'Parametr (Cecha X)': feature_names, 'Znaczenie Względne': importances})
    df_imp = df_imp.sort_values(by='Znaczenie Względne', ascending=False)
    
    # 7. Zapis wyników
    os.makedirs(os.path.dirname(PATH_PRED_OUT), exist_ok=True)
    df_pred = pd.DataFrame({
        'ring': rings_test,
        'D_Vloss_real': y_test.values,
        'D_Vloss_pred': y_pred_test
    })
    df_pred.to_csv(PATH_PRED_OUT, index=False)
    
    # 8. Generowanie wykresu porównawczego
    os.makedirs(os.path.dirname(PATH_FIG_OUT), exist_ok=True)
    plt.figure(figsize=(15, 6))
    
    plt.plot(rings_all, df['D_Vloss'], color='gray', linestyle='-', linewidth=1, alpha=0.3)
    plt.scatter(rings_all, y, color='black', marker='o', s=15, alpha=0.6, label='Wartość rzeczywista (Kriging)')
    plt.scatter(rings_train, y_pred_train, color='royalblue', marker='x', s=25, alpha=0.8, label='Predykcja - Trening')
    plt.scatter(rings_test, y_pred_test, color='crimson', marker='*', s=40, alpha=0.9, label='Predykcja - Test')
    plt.axvline(x=SPLIT_RING, color='darkgreen', linestyle='--', linewidth=2.5, label=f'Granica podziału ({SPLIT_RING})')
       
    y_max_plot = df['D_Vloss'].max() * 1.05
    plt.title(f"Wyniki predykcji ubytku objętości gruntu - Model XGBoost", fontsize=12, pad=15)
    plt.xlabel("Numer ringu", fontsize=11)
    plt.ylabel("Zmienna celu: V_loss [%]", fontsize=11)
    plt.xlim(0, df['ring'].max() + 5)
    plt.ylim(-0.05, y_max_plot)
    plt.grid(True, linestyle=':', alpha=0.5)
    plt.legend(loc='lower left', frameon=True, shadow=True)
    
    plt.savefig(PATH_FIG_OUT, bbox_inches='tight', dpi=300)
    plt.close()
    
    # 9. Zapis raportu tekstowego do pliku
    os.makedirs(os.path.dirname(PATH_REPORT_OUT), exist_ok=True)
    with open(PATH_REPORT_OUT, 'w') as f:
        f.write("=== RAPORT METODOLOGICZNY ML - XGBOOST (STABILNY) ===\n")
        f.write(f"Zoptymalizowane hiperparametry: {best_params}\n")
    
    # 10. WYŚWIETLENIE RAPORTU W TERMINALU
    print("\n" + "#"*55)
    print("   RAPORT KOŃCOWY W KONSOLI (XGBOOST - STABILNY)")
    print("#"*55)
    print(f"Wybrane parametry: {best_params}")
    print("\nTop 5 najważniejszych cech według XGBoost:")
    print(df_imp.head(10).to_string(index=False))
    print("-" * 55)
    print(f"Trening -> MAE: {mae_train:.3f}% | RMSE: {rmse_train:.3f}% | RMAE: {rmae_train:.1f}% | R2: {r2_train:.3f}")
    print(f"Test    -> MAE: {mae_test:.3f}% | RMSE: {rmse_test:.3f}% | RMAE: {rmae_test:.1f}% | R2: {r2_test:.3f}")
    print("#"*55 + "\n")

if __name__ == "__main__":
    run_xgboost_pipeline()