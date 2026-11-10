import numpy as np
import scipy.signal as signal
import matplotlib.pyplot as plt

# Overføringsfunktion: H(s) = 60s / (s^2 + 8s + 15)
num = [60, 0]
den = [1, 8, 15]
sys = signal.TransferFunction(num, den)

# Udvalgte testfrekvenser [rad/s]
omegas = [0.5, np.sqrt(15), 30.0]

fig, axes = plt.subplots(len(omegas), 1, figsize=(9, 8), sharex=False)

for i, w in enumerate(omegas):
    # Teoretisk værdi
    s_val = 1j * w
    h_val = (60 * s_val) / (s_val**2 + 8 * s_val + 15)
    mag_th = np.abs(h_val)
    phase_th = np.angle(h_val, deg=True)
    
    # Tidssimulering over tilstrækkeligt mange perioder
    period = 2 * np.pi / w
    t_settle = 3.0  # Tid for transienters udklingning (tau = 1/3 s)
    t_end = max(8 * period, t_settle + 3 * period)
    t = np.linspace(0, t_end, 4000)
    u = np.sin(w * t)
    
    t_out, y_out, _ = signal.lsim(sys, U=u, T=t)
    
    # Udsnit af de sidste to perioder (stationær tilstand)
    mask = t >= (t_end - 2 * period)
    t_ss = t[mask] - t[mask][0]
    u_ss = u[mask]
    y_ss = y_out[mask]
    
    # Målt amplitude i simuleringen
    mag_sim = (np.max(y_ss) - np.min(y_ss)) / 2.0
    
    # Plotning
    ax = axes[i]
    ax.plot(t_ss, u_ss, 'k--', label=f'Input: $u(t)$ (amp = 1.0)')
    ax.plot(t_ss, y_ss, 'b-', linewidth=1.8, 
            label=f'Output: $y(t)$ (målt peak = {mag_sim:.2f})')
    ax.set_title(f'$\\omega = {w:.2f}$ rad/s | Teoretisk: $|H| = {mag_th:.2f}$, fase = {phase_th:.1f}°')
    ax.set_ylabel('Amplitude')
    ax.grid(True, linestyle=':', alpha=0.6)
    ax.legend(loc='upper right')

axes[-1].set_xlabel('Tid [s] i stationær tilstand')
plt.tight_layout()
plt.show()