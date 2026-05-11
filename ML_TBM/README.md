# Machine Learning for TBM Settlement Prediction

## Project Status: Active Development (Feature Engineering Phase)
This project is part of a Master's Thesis focusing on predicting $V_{loss}$ by ground surface deformations induced by Tunnel Boring Machines (TBM). It bridges the gap between raw geostatistical telemetry and advanced predictive modeling.

## Project Overview
Predicting surface settlement is critical for the safety of urban infrastructure during tunneling. This project implements a full **end-to-end Machine Learning pipeline** to transform raw TBM sensor data into accurate $V_{loss}$.

### Key Technical Highlights:
* **Data Infrastructure:** SQL-based RDBMS architecture for managing Big Data telemetry.
* **Performance:** Accelerated data processing using **Parquet** format and **GPU hardware** (NVIDIA RTX 4090).
* **Scope:** Analyzing 238 rings of  machine parameters synchronized with surface monitoring.

## Engineering Data Pipeline
The repository follows a strict modular structure to ensure reproducibility of the research:

1. **Extraction & Coordination:** `01-05` Scripts handle coordinate transformations and metadata synchronization between the machine and surface sensors.
2. **Data Cleaning & Management:** `06-10` Scripts manage SQL database extraction and telemetry noise reduction.
3. **Audit & Diagnostics:** `11-11c` Scripts provide spatial audits and diagnostic reports on ring data quality.
4. **Ground Truth Calculation:** `12_kriging_volume.py` implements spatial interpolation by **Kriging** to calculate the actual Volume Loss ($V_{loss}$) for model training.

## Planned Architectures (Comparative Study)
The research objective is to compare how different architectures handle limited engineering datasets:
* **Baseline:** Multiple Linear Regression (MLR).
* **Ensemble:** Random Forest & XGBoost (Optimized for tabular data).
* **Deep Learning:** - **TCN (Temporal Convolutional Networks):** Selected over LSTM for better gradient stability and efficient long-term dependency mapping in time-series telemetry.

## Tech Stack
* **Language:** Python 3.10+
* **Data Science:**  Scikit-learn, XGBoost, PyTorch, Pandas, NumPy.
* **Database:** SQL (RDBMS), Parquet.
* **Hardware:** CUDA-enabled GPU acceleration.

## Roadmap
- [x] SQL Database architecture & Data cleaning.
- [x] Geostatistical data calculation.
- [ ] **Current Phase:** Feature Engineering.
- [ ] Model benchmarking & Hyperparameter optimization.
- [ ] Comparative analysis of DL vs. Classical methods by statistical method like (RMSE, MAE, $R^2$) and model training time.
