import pandas as pd
import numpy as np
import time
import os
import matplotlib.pyplot as plt
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import copy
import joblib
import json  # <-- DODANO: Do zapisu hiperparametrów

# Wymaga: pip install torch torchvision torchaudio
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset

# --- SPRAWDZENIE GPU ---
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"[SYSTEM] Obliczenia Deep Learning uruchomione na: {device.type.upper()}")

# =====================================================================
# --- IDENTYFIKATOR TESTU (ZMIENIAJ PRZY GRINDOWANIU!) ---
# =====================================================================
TEST_ID = "v12"

# --- KONFIGURACJA ŚCIEŻEK ---
PATH_INPUT = r"D:\%PRACA_MAGISTERSKA\data\processed\ml_dataset_podejscie_A.parquet"
PATH_REPORT_OUT = rf"D:\%PRACA_MAGISTERSKA\results\reports\lstm_report_{TEST_ID}.txt"
PATH_PRED_OUT = rf"D:\%PRACA_MAGISTERSKA\results\models\lstm_predictions_{TEST_ID}.csv"
PATH_FIG_OUT = rf"D:\%PRACA_MAGISTERSKA\results\figures\lstm_predictions_plot_{TEST_ID}.png"

# Ścieżki do ZAPISU modelu, skalera i PARAMETRÓW
PATH_MODEL_OUT = rf"D:\%PRACA_MAGISTERSKA\results\models\lstm_weights_{TEST_ID}.pth"
PATH_SCALER_OUT = rf"D:\%PRACA_MAGISTERSKA\results\models\lstm_scaler_{TEST_ID}.pkl"
PATH_PARAMS_OUT = rf"D:\%PRACA_MAGISTERSKA\results\models\lstm_hyperparams_{TEST_ID}.json"

SPLIT_RING = 225

# --- ZAAWANSOWANE HIPERPARAMETRY DLA LSTM ---
TIME_STEPS = 2         # Okno czasowe (ile ringów wstecz)
LSTM_UNITS = 32         # Pojemność komórki pamięci
NUM_LAYERS = 3         # Dwie warstwy LSTM (Deep)
DROPOUT_RATE = 0.2      # Regularyzacja
LEARNING_RATE = 0.001   # Krok uczenia
WEIGHT_DECAY = 1e-4     # Regularyzacja L2 wag w optymalizatorze
EPOCHS = 400            # Maksymalna liczba epok
BATCH_SIZE = 8          # Rozmiar paczki
PATIENCE = 20           # Early Stopping

# --- DEFINICJA ARCHITEKTURY SIECI ---
class TBM_LSTM(nn.Module):
    def __init__(self, input_dim, hidden_dim, num_layers, dropout_rate):
        super(TBM_LSTM, self).__init__()
        self.lstm = nn.LSTM(input_dim, hidden_dim, num_layers=num_layers, 
                            batch_first=True, dropout=dropout_rate if num_layers > 1 else 0)
        
        self.dropout = nn.Dropout(dropout_rate)
        self.fc1 = nn.Linear(hidden_dim, 32)
        self.relu = nn.ReLU()
        self.fc2 = nn.Linear(32, 1)

    def forward(self, x):
        lstm_out, _ = self.lstm(x)
        last_time_step_out = lstm_out[:, -1, :]
        x = self.dropout(last_time_step_out)
        x = self.relu(self.fc1(x))
        x = self.fc2(x)
        return x

def run_lstm_pipeline():
    print("="*60)
    print(f"   TRENOWANIE SIECI PyTorch Deep LSTM (Wersja: {TEST_ID})")
    print("="*60)
    
    df = pd.read_parquet(PATH_INPUT)
    df = df.sort_values(by='ring').reset_index(drop=True)
    
    feature_cols = [c for c in df.columns if c not in ['ring', 'D_Vloss']]
    rings_all = df['ring'].values
    y_all = df['D_Vloss'].values
    
    # Standaryzacja
    train_mask_for_scaling = df['ring'] <= SPLIT_RING
    scaler_X = StandardScaler()
    scaler_X.fit(df.loc[train_mask_for_scaling, feature_cols])
    X_scaled_all = scaler_X.transform(df[feature_cols])
    
    # Sekwencje 3D
    X_seq, y_seq, rings_seq = [], [], []
    for i in range(len(X_scaled_all) - TIME_STEPS):
        X_seq.append(X_scaled_all[i : i + TIME_STEPS])
        y_seq.append(y_all[i + TIME_STEPS])
        rings_seq.append(rings_all[i + TIME_STEPS])
        
    X_seq = np.array(X_seq)
    y_seq = np.array(y_seq).reshape(-1, 1)
    rings_seq = np.array(rings_seq)
    
    # Podział
    train_idx = rings_seq <= SPLIT_RING
    test_idx = rings_seq > SPLIT_RING
    X_train_np, y_train_np = X_seq[train_idx], y_seq[train_idx]
    X_test_np, y_test_np = X_seq[test_idx], y_seq[test_idx]
    rings_train, rings_test = rings_seq[train_idx], rings_seq[test_idx]
    
    val_size = int(len(X_train_np) * 0.15)
    X_train_sub_np, y_train_sub_np = X_train_np[:-val_size], y_train_np[:-val_size]
    X_val_np, y_val_np = X_train_np[-val_size:], y_train_np[-val_size:]
    
    X_train_t = torch.tensor(X_train_sub_np, dtype=torch.float32).to(device)
    y_train_t = torch.tensor(y_train_sub_np, dtype=torch.float32).to(device)
    X_val_t = torch.tensor(X_val_np, dtype=torch.float32).to(device)
    y_val_t = torch.tensor(y_val_np, dtype=torch.float32).to(device)
    
    train_dataset = TensorDataset(X_train_t, y_train_t)
    train_loader = DataLoader(train_dataset, batch_size=BATCH_SIZE, shuffle=False)
    
    input_dim = len(feature_cols)
    model = TBM_LSTM(input_dim, LSTM_UNITS, NUM_LAYERS, DROPOUT_RATE).to(device)
    
    criterion = nn.MSELoss() 
    optimizer = optim.Adam(model.parameters(), lr=LEARNING_RATE, weight_decay=WEIGHT_DECAY)
    
    start_time = time.perf_counter()
    best_val_loss = float('inf')
    patience_counter = 0
    best_model_weights = copy.deepcopy(model.state_dict())
    
    for epoch in range(EPOCHS):
        model.train() 
        for batch_X, batch_y in train_loader:
            optimizer.zero_grad()           
            predictions = model(batch_X)    
            loss = criterion(predictions, batch_y) 
            loss.backward()                 
            optimizer.step()                
            
        model.eval() 
        with torch.no_grad(): 
            val_preds = model(X_val_t)
            val_loss = criterion(val_preds, y_val_t).item()
            
        if val_loss < best_val_loss:
            best_val_loss = val_loss
            best_model_weights = copy.deepcopy(model.state_dict())
            patience_counter = 0
        else:
            patience_counter += 1
            
        if patience_counter >= PATIENCE:
            break

    end_time = time.perf_counter()
    model.load_state_dict(best_model_weights)
    
    model.eval()
    with torch.no_grad():
        X_train_all_t = torch.tensor(X_train_np, dtype=torch.float32).to(device)
        X_test_all_t = torch.tensor(X_test_np, dtype=torch.float32).to(device)
        y_pred_train = model(X_train_all_t).cpu().numpy().flatten()
        y_pred_test = model(X_test_all_t).cpu().numpy().flatten()
        
    y_train_flat, y_test_flat = y_train_np.flatten(), y_test_np.flatten()
    
    # OBLICZANIE METRYK (w tym RMAE)
    mae_train = mean_absolute_error(y_train_flat, y_pred_train)
    mae_test = mean_absolute_error(y_test_flat, y_pred_test)
    rmse_train = np.sqrt(mean_squared_error(y_train_flat, y_pred_train))
    rmse_test = np.sqrt(mean_squared_error(y_test_flat, y_pred_test))
    
    rmae_train = (mae_train / np.mean(np.abs(y_train_flat))) * 100
    rmae_test = (mae_test / np.mean(np.abs(y_test_flat))) * 100
    
    r2_train = r2_score(y_train_flat, y_pred_train)
    r2_test = r2_score(y_test_flat, y_pred_test)
    
    # Zapis plików
    os.makedirs(os.path.dirname(PATH_PRED_OUT), exist_ok=True)
    pd.DataFrame({'ring': rings_test, 'D_Vloss_real': y_test_flat, 'D_Vloss_pred': y_pred_test}).to_csv(PATH_PRED_OUT, index=False)
    
    os.makedirs(os.path.dirname(PATH_FIG_OUT), exist_ok=True)
    plt.figure(figsize=(15, 6))
    plt.plot(rings_all, y_all, color='gray', linestyle='-', linewidth=1, alpha=0.3)
    plt.scatter(rings_all, y_all, color='black', marker='o', s=15, alpha=0.6, label='Wartość rzeczywista')
    plt.scatter(rings_train, y_pred_train, color='royalblue', marker='x', s=25, alpha=0.8, label='Predykcja - Trening')
    plt.scatter(rings_test, y_pred_test, color='crimson', marker='*', s=40, alpha=0.9, label='Predykcja - Test')
    plt.axvline(x=SPLIT_RING, color='darkgreen', linestyle='--', linewidth=2.5)
    
    plt.title(f"Wyniki predykcji - Deep LSTM ({TEST_ID})\n[TEST] MAE: {mae_test:.3f}% | RMSE: {rmse_test:.3f}% | RMAE: {rmae_test:.1f}% | R2: {r2_test:.3f}", fontsize=12, pad=15)
    plt.xlabel("Numer ringu", fontsize=11)
    plt.ylabel("Zmienna celu: V_loss [%]", fontsize=11)
    plt.xlim(0, df['ring'].max() + 5)
    plt.ylim(-0.05, df['D_Vloss'].max() * 1.05)
    plt.grid(True, linestyle=':', alpha=0.5)
    plt.legend(loc='upper left', frameon=True, shadow=True)
    
    plt.savefig(PATH_FIG_OUT, bbox_inches='tight', dpi=300)
    plt.close()
    
    # --- ZAPIS MODELU, SKALERA I PARAMETRÓW ---
    torch.save(model.state_dict(), PATH_MODEL_OUT)
    joblib.dump(scaler_X, PATH_SCALER_OUT)
    
    # Tworzymy słownik z parametrami i metrykami (w tym RMAE)
    hyperparams_log = {
        "TEST_ID": TEST_ID,
        "TIME_STEPS": TIME_STEPS,
        "LSTM_UNITS": LSTM_UNITS,
        "NUM_LAYERS": NUM_LAYERS,
        "DROPOUT_RATE": DROPOUT_RATE,
        "LEARNING_RATE": LEARNING_RATE,
        "WEIGHT_DECAY": WEIGHT_DECAY,
        "EPOCHS": EPOCHS,
        "BATCH_SIZE": BATCH_SIZE,
        "PATIENCE": PATIENCE,
        "METRICS": {
            "Train_R2": round(r2_train, 4),
            "Test_R2": round(r2_test, 4),
            "Train_MAE": round(mae_train, 4),
            "Test_MAE": round(mae_test, 4),
            "Train_RMAE_pct": round(rmae_train, 2),
            "Test_RMAE_pct": round(rmae_test, 2)
        }
    }
    
    # Zapisujemy do pliku JSON
    with open(PATH_PARAMS_OUT, 'w', encoding='utf-8') as f:
        json.dump(hyperparams_log, f, indent=4)
    
    print("\n" + "#"*55)
    print(f"   RAPORT KOŃCOWY W KONSOLI (PyTorch LSTM - {TEST_ID})")
    print("#"*55)
    print(f"Czas treningu sieci: {end_time - start_time:.2f}s")
    print("-" * 55)
    print(f"Trening -> MAE: {mae_train:.3f}% | RMSE: {rmse_train:.3f}% | RMAE: {rmae_train:.1f}% | R2: {r2_train:.3f}")
    print(f"Test    -> MAE: {mae_test:.3f}% | RMSE: {rmse_test:.3f}% | RMAE: {rmae_test:.1f}% | R2: {r2_test:.3f}")
    print("-" * 55)
    print(f"[ZAPISANO WAGI]: {PATH_MODEL_OUT}")
    print(f"[ZAPISANO SKALER]: {PATH_SCALER_OUT}")
    print(f"[ZAPISANO PARAMETRY]: {PATH_PARAMS_OUT}")
    print("#"*55 + "\n")

if __name__ == "__main__":
    run_lstm_pipeline()