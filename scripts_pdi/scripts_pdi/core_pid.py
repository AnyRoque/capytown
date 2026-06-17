#!/usr/bin/env python3
"""CapyTown scripts_pdi — nucleo compartido del simulador PID de rumbo.

Modelo: cinematica de uniciclo con retardo de actuador de primer orden
(el robot no alcanza la velocidad angular comandada al instante, la
aproxima con constante de tiempo tau). Es la misma ecuacion y los mismos
limites (saturacion, anti-windup) que el nodo lane_controller real.
"""
import math
import numpy as np


def normalize(a: float) -> float:
    """Normaliza un angulo a [-pi, pi]."""
    return (a + math.pi) % (2.0 * math.pi) - math.pi


def simular(kp, ki, kd, modo="giro90", t_fin=6.0, dt=1.0 / 30.0,
            tau=0.15, max_w=2.0, i_limit=0.5, ruido=0.0, semilla=7):
    """Simula el lazo de rumbo. Devuelve dict con t, error_deg, yaw_deg, setpoint_deg."""
    rng = np.random.default_rng(semilla)
    theta, w = 0.0, 0.0
    setp = math.radians(90.0) if modo == "giro90" else 0.0
    if modo == "recto":
        theta = math.radians(12.0)   # perturbacion inicial: alguien movio al chaski
    integral, e_prev = 0.0, None
    T, E, TH = [], [], []
    for k in range(int(t_fin / dt)):
        medicion = theta + rng.normal(0.0, ruido)
        e = normalize(setp - medicion)
        # --- PID con anti-windup y saturacion (igual que el nodo real) ---
        integral = max(-i_limit, min(i_limit, integral + e * dt))
        d = 0.0 if e_prev is None else (e - e_prev) / dt
        e_prev = e
        w_cmd = kp * e + ki * integral + kd * d
        w_cmd = max(-max_w, min(max_w, w_cmd))
        # --- dinamica del actuador (retardo de primer orden) ---
        w += (w_cmd - w) * dt / tau
        theta += w * dt
        T.append(k * dt); E.append(math.degrees(e)); TH.append(math.degrees(theta))
    return {"t": np.array(T), "error_deg": np.array(E),
            "yaw_deg": np.array(TH), "setpoint_deg": math.degrees(setp)}


def metricas(sim):
    """Sobreimpulso (%), tiempo de asentamiento (banda +-2 deg) y error final (deg)."""
    t, th, sp = sim["t"], sim["yaw_deg"], sim["setpoint_deg"]
    ref = sp if sp != 0 else th[0]            # giro90: 90 ; recto: perturbacion inicial
    sobre = max(0.0, (th.max() - sp)) / abs(ref) * 100.0 if ref else 0.0
    dentro = np.abs(th - sp) <= 2.0
    t_asent = next((t[i] for i in range(len(t)) if dentro[i:].all()), None)
    return {"sobreimpulso_pct": sobre, "t_asentamiento_s": t_asent,
            "error_final_deg": abs(sp - th[-1])}
