# Composite Structural Analysis — AGH Solar Boat Team

##  Overview
This project presents the structural design, numerical analysis, and optimization of composite bulkheads for the **"Delta"** solar racing boat. As a member of the **AGH Solar Boat Team** (Construction Section), I managed the full workflow: from high-fidelity composite modeling in **Ansys ACP** to verifying failure criteria for racing conditions.

### Verification:
The composite structure was validated against extreme load cases using specialized criteria:
* **Failure Theories**: Tsai-Wu and Puck criteria were applied to evaluate ply-by-ply integrity.
* **Operational Cases**: Verified for boat hoisting (lifting straps) and hydrodynamic water pressure during racing.

## Engineering Details
* **Organization**: AGH Solar Boat Team (Section: Construction).
* **Software**: Ansys ACP (Composite PrepPost), Ansys Mechanical, SolidWorks.
* **Materials**: Carbon Fiber Reinforced Polymer (CFRP) – sandwich structure with a foam core.
* **Key Skills**: Rosette definition, selection rules, selection groups, selection stacking, and composite post-processing.

## Key Results
* **Failure Index**: Maximum Tsai-Wu index reached **0.42**, confirming a high safety margin (target < 1.0).
* **Weight Optimization**: Successfully reduced composite layers in low-stress zones, decreasing overall weight without compromising stiffness.
* **Manufacturing Support**: Simulation results directly determined the final layup schedule used in the vacuum bagging process.

![Failure Analysis](./images/failure_results.png) 
*Figure 1: Tsai-Wu failure index distribution across critical composite plies.*

## Project Structure
* `Composite_Bulkhead_Analysis.md` – Detailed technical report on the ACP workflow and structural results.
* `Modelowanie i symulacja kompozytów w Ansys ACP.pdf` – **Technical Case Study & Workflow**: A comprehensive guide covering the end-to-end composite simulation process for high-performance racing applications.
