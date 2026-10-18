# Rafał Sypniewski | CAE & Simulation Portfolio

Mechanical Engineer specializing in bridging FEA simulations with Python/ML automation and custom numerical solvers.

---

## Tech Stack

* **Structural FEA:** Ansys Mechanical (incl. ACP composites), Abaqus (Standard), CalculiX (PrePoMax), MIDAS GTS NX (basic geotechnical analyses), HyperMesh (basics). Linear static analysis, composite layups.
* **CFD:** Ansys Fluent, OpenFOAM (blockMesh, snappyHexMesh, simpleFoam), RANS turbulence modelling (k-ω SST), ParaView, CFD-Post.
* **Coupled Physics & Verification:** One-way FSI (CFD-to-FEA pressure mapping), mesh-convergence and mesh-quality studies, cross-solver verification, Design of Experiments (DOE, response surface methodology).
* **Programming:** Python (Pandas, NumPy, Scikit-learn, XGBoost, PyTorch, Matplotlib), MATLAB (Numerical Solvers, Symbolic Math, Visualization), SQL, Linux (Ubuntu/WSL).
* **CAD:** NX (Siemens), Autodesk Fusion, SolidWorks, Inventor, FreeCAD.
* **Data Science:** Feature Engineering, Large-scale measurement data processing (Parquet), SQL-based RDBMS, GPU Acceleration (CUDA).
---

## Key Projects (Project Highlights)

I specialize in bridging the gap between **Classical Finite Element Analysis** and **Modern Data Science**. My work focuses on structural integrity, thermal management, and engineering process automation.

| Project | Engineering & Technical Focus | Tech Stack | Resources |
| :--- | :--- | :--- | :--- |
| **ML for TBM Settlement Prediction** | End-to-end pipeline for **surface settlement ($V_{loss}$)** prediction from real-world TBM telemetry: SQL/Parquet ETL, 4-method geostatistical ground truth, feature engineering, and a Linear/Random Forest/XGBoost/LSTM model benchmark. | Python, SQL, PyTorch, GPU | [Explore](./ML_TBM/) |
| **High-Order FEM Thermal Solver** | Built a steady-state thermal solver from scratch using **9-node quadrilateral elements**. Includes manual **Global Stiffness Matrix** assembly. Verified vs. Ansys with a relative error of **0.008%**. | MATLAB, Ansys Mechanical | [Explore](./FEM_Thermal_Solver/) |
| **Composite FEA simulation of Bulkheads** | Structural optimization of bulkhead systems for racing boats. Implemented complex **laminate layups** and sandwich structures using **Ansys ACP** to maximize stiffness-to-weight ratio. | Ansys ACP, Fusion 360 | [Explore](./Composite_FEA_Bulkheads/) |
| **Wind-Load FSI Analysis** | Coupled **Fluid-Structure Interaction (FSI)** simulations. Mapping pressure fields from **Ansys Fluent** to mechanical structures to evaluate stress and SF under extreme wind conditions. | Ansys Fluent, Ansys Mechanical | [Explore](./FSI_Solar/) |
| **Open-Source FSI Workflow** | The same wind-load FSI case rebuilt with **open-source tools only**: OpenFOAM meshing and CFD (snappyHexMesh, simpleFoam, k-ω SST) on Linux with an 8-core MPI run, pressure mapped onto a **CalculiX** model. Documents known limitations and next steps. | OpenFOAM, CalculiX/PrePoMax, ParaView, FreeCAD | [Explore](./FSI_OpenSource/) |

--- 

**Contact:** rafaloficial@gmail.com | [LinkedIn Profile](https://www.linkedin.com/in/rafalsypniewski) | Kraków, PL
