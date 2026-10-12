import numpy as np
import math
# --- INDTAST JERES MÅLTE R-VÆRDIER HER ---
# (Bemærk: T-værdierne er faste antagelser)
T1_K, R1 = 273.15 + 10 ,    10946 # 0 °C (Eksempel: 32.55 kΩ)
T2_K, R2 = 273.15 + 50,     3417 # 42 °C (Eksempel: 7.24 kΩ)
T3_K, R3 = 273.15 + 90,     990 # 100 °C (Eksempel: 1.18 kΩ)
# Lav logaritme-værdierne
L1 = math.log(R1)
L2 = math.log(R2)
L3 = math.log(R3)
# Opstil Y-vektor (1/T)
Y = np.array([1/T1_K, 1/T2_K, 1/T3_K])
# Opstil X-matrix (1, ln(R), ln(R)^3)
X = np.array([
[1, L1, L1**3],
[1, L2, L2**3],
[1, L3, L3**3]
])
# Løs for P = [A, B, C]
P = np.linalg.solve(X, Y)
A, B, C = P[0], P[1], P[2]
print(f"Steinhart-Hart Parametre:")
print(f"A = {A:.10e}")
print(f"B = {B:.10e}")
print(f"C = {C:.10e}")