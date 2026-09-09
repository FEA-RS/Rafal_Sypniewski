import pandas as pd
import numpy as np
import os
import matplotlib.pyplot as plt
import joblib
import torch
import torch.nn as nn
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

# --- JAKĄ WERSJĘ MODELU CHCESZ ODTWORZYĆ? ---
LOAD_TEST_ID = "v11"

# Musisz podać dokładnie te same parametry, z którymi trenowałeś dany model!
TIME_STEPS = 2
LSTM_UNITS = 32
NUM_LAYERS = 3
DROPOUT_RATE = 0.2

# --- ŚCIEŻKI ---
PATH_INPUT = r"D:\%PRACA_MAGISTERSKA\data\processed\ml_dataset_podejscie_A.parquet"
PATH_MODEL_IN = rf"D:\%PRACA_MAGISTERSKA\results\models\lstm_weights_{LOAD_TEST_ID}.pth"
PATH_SCALER_IN = rf"D:\%PRACA_MAGISTERSKA\results\models\lstm_scaler_{LOAD_TEST_ID}.pkl"
PATH_FIG_OUT = rf"D:\%PRACA_MAGISTERSKA\results\figures\lstm_REPRODUCED_{LOAD_TEST_ID}.png"
SPLIT_RING = 225

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# Klasa sieci musi być tu zdefiniowana (tzw. "ciało"), żeby załadować do niej "mózg"
class TBM_LSTM(nn.Module):
    def __init__(self, input_dim, hidden_dim, num_layers, dropout_rate):
        super(TBM_LSTM, self).__init__()
        self.lstm = nn.LSTM(input_dim, hidden_dim, num_layers=num_layers, batch_first=True)
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

def reproduce():
    print(f"-> Odtwarzam model z zapisanych wag: {LOAD_TEST_ID}")
    
    # 1. Wczytanie danych
    df = pd.read_parquet(PATH_INPUT).sort_values(by='ring').reset_index(drop=True)
    feature_cols = [c for c in df.columns if c not in ['ring', 'D_Vloss']]
    rings_all, y_all = df['ring'].values, df['D_Vloss'].values
    
    # 2. Wczytanie skalera (zamiast uczenia nowego!)
    scaler_X = joblib.load(PATH_SCALER_IN)
    X_scaled_all = scaler_X.transform(df[feature_cols])
    
    # 3. Sekwencje
    X_seq, y_seq, rings_seq = [], [], []
    for i in range(len(X_scaled_all) - TIME_STEPS):
        X_seq.append(X_scaled_all[i : i + TIME_STEPS])
        y_seq.append(y_all[i + TIME_STEPS])
        rings_seq.append(rings_all[i + TIME_STEPS])
        
    X_seq, y_seq, rings_seq = np.array(X_seq), np.array(y_seq).reshape(-1, 1), np.array(rings_seq)
    
    train_idx = rings_seq <= SPLIT_RING
    test_idx = rings_seq > SPLIT_RING
    X_train_np, y_train_np = X_seq[train_idx], y_seq[train_idx]
    X_test_np, y_test_np = X_seq[test_idx], y_seq[test_idx]
    rings_train, rings_test = rings_seq[train_idx], rings_seq[test_idx]
    
    # 4. Inicjalizacja "pustego" modelu i wgranie wag z dysku
    input_dim = len(feature_cols)
    model = TBM_LSTM(input_dim, LSTM_UNITS, NUM_LAYERS, DROPOUT_RATE).to(device)
    
    # MAGICZNA LINIA: Ładujemy wiedzę
    model.load_state_dict(torch.load(PATH_MODEL_IN, weights_only=True))
    model.eval() # Ważne: wyłącza dropout dla odtwarzania!
    
    # 5. Predykcja i Metryki
    with torch.no_grad():
        y_pred_train = model(torch.tensor(X_train_np, dtype=torch.float32).to(device)).cpu().numpy().flatten()
        y_pred_test = model(torch.tensor(X_test_np, dtype=torch.float32).to(device)).cpu().numpy().flatten()
        
    y_train_flat, y_test_flat = y_train_np.flatten(), y_test_np.flatten()
    
    # --- OBLICZANIE METRYK DLA TRENINGU I TESTU ---
    mae_train = mean_absolute_error(y_train_flat, y_pred_train)
    rmse_train = np.sqrt(mean_squared_error(y_train_flat, y_pred_train))
    rmae_train = (mae_train / np.mean(np.abs(y_train_flat))) * 100
    r2_train = r2_score(y_train_flat, y_pred_train)
    
    mae_test = mean_absolute_error(y_test_flat, y_pred_test)
    rmse_test = np.sqrt(mean_squared_error(y_test_flat, y_pred_test))
    rmae_test = (mae_test / np.mean(np.abs(y_test_flat))) * 100
    r2_test = r2_score(y_test_flat, y_pred_test)
    
# 6. Rysowanie
    os.makedirs(os.path.dirname(PATH_FIG_OUT), exist_ok=True)
    plt.figure(figsize=(15, 6))
    
    plt.plot(rings_all, y_all, color='gray', linestyle='-', linewidth=1, alpha=0.3)
    plt.scatter(rings_all, y_all, color='black', marker='o', s=15, alpha=0.6, label='Wartość rzeczywista')
    plt.scatter(rings_train, y_pred_train, color='royalblue', marker='x', s=25, alpha=0.8, label='Predykcja - Trening')
    plt.scatter(rings_test, y_pred_test, color='crimson', marker='*', s=40, alpha=0.9, label='Predykcja - Test')
    plt.axvline(x=SPLIT_RING, color='darkgreen', linestyle='--', linewidth=2.5, label=f'Granica podziału (Ring {SPLIT_RING})')
    
    # Zamiana df['D_Vloss'] na y_all
    y_max_plot = y_all.max() * 1.05
    plt.text(110, y_max_plot * 0.9, 'STREFA UCZENIA MODELU\n(Ringi 1-225)', 
             color='darkgreen', fontsize=10, fontweight='bold', ha='center',
             bbox=dict(facecolor='white', alpha=0.8, edgecolor='none'))
    
    plt.text(255, y_max_plot * 0.9, 'STREFA TESTOWA\n(Ringi 226-285)', 
             color='crimson', fontsize=10, fontweight='bold', ha='center',
             bbox=dict(facecolor='white', alpha=0.8, edgecolor='none'))
    
    plt.title(f"Wyniki predykcji ubytku objętości gruntu - Model LSTN", fontsize=12, pad=15)
    plt.xlabel("Numer ringu", fontsize=11)
    plt.ylabel("Zmienna celu: V_loss [%]", fontsize=11)
    
    # Zamiana df['ring'] na rings_all
    plt.xlim(0, rings_all.max() + 5)
    plt.ylim(-0.05, y_max_plot)
    plt.grid(True, linestyle=':', alpha=0.5)
    plt.legend(loc='lower left', frameon=True, shadow=True)
    
    plt.savefig(PATH_FIG_OUT, bbox_inches='tight', dpi=300)
    plt.close()

    print(f"-> [GOTOWE] Idealnie odtworzono wykres z modelu {LOAD_TEST_ID} z dodanym RMAE!")
    
    # --- DODANE: WYŚWIETLANIE RAPORTU W KONSOLI ---
    print("\n" + "#"*55)
    print(f"   RAPORT ODTWORZONY W KONSOLI (PyTorch LSTM - {LOAD_TEST_ID})")
    print("#"*55)
    print(f"Trening -> MAE: {mae_train:.3f}% | RMSE: {rmse_train:.3f}% | RMAE: {rmae_train:.1f}% | R2: {r2_train:.3f}")
    print(f"Test    -> MAE: {mae_test:.3f}% | RMSE: {rmse_test:.3f}% | RMAE: {rmae_test:.1f}% | R2: {r2_test:.3f}")
    print("#"*55 + "\n")

if __name__ == "__main__":
    reproduce()