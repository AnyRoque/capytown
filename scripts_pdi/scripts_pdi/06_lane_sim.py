#!/usr/bin/env python3
"""CapyTown scripts_pdi/06 — Simulador de lane following (Escenario A virtual).

Circuito tipo "estadio" (2 rectas + 2 semicirculos, escala del Tambo 2x2 m).
El robot es un uniciclo con retardo de actuador; el error lateral se mide
geometricamente en un punto look-ahead (como hace la camara + IPM) y un PID
identico al del nodo real publica omega. Reproduce el flujo del RC-2:
3 vueltas, curva de /lane_error y metricas de la rubrica.

Uso:
  python3 06_lane_sim.py --kp 2.5 --kd 0.3 --vueltas 3
  python3 06_lane_sim.py --kp 6.0 --vueltas 1 --ruido 0.005   # zigzag asegurado
"""
import argparse
import math
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# --- circuito estadio: rectas de L=1.0 m, radio de curva R=0.5 m (centro del carril)
L, R = 1.0, 0.5
LANE_HALF = 0.105                      # medio carril CapyTown (m)
PERIM = 2 * L + 2 * math.pi * R


def centerline(s):
    """Punto (x,y) y tangente (tx,ty) de la linea central a la distancia s (mod perimetro)."""
    s = s % PERIM
    if s < L:                                   # recta inferior ->
        return np.array([s, 0.0]), np.array([1.0, 0.0])
    s -= L
    if s < math.pi * R:                         # curva derecha (sube)
        a = s / R
        c = np.array([L + R * math.sin(a), R - R * math.cos(a)])
        return c, np.array([math.cos(a), math.sin(a)])
    s -= math.pi * R
    if s < L:                                   # recta superior <-
        return np.array([L - s, 2 * R]), np.array([-1.0, 0.0])
    s -= L
    a = s / R                                   # curva izquierda (baja)
    return np.array([-R * math.sin(a), R + R * math.cos(a)]), np.array([-math.cos(a), -math.sin(a)])


# polilinea densa para buscar el punto mas cercano
S_DENSO = np.linspace(0, PERIM, 4000, endpoint=False)
PTS = np.array([centerline(s)[0] for s in S_DENSO])
TGT = np.array([centerline(s)[1] for s in S_DENSO])


def error_lateral(p):
    """Error lateral con signo (>0: carril a la derecha del robot... segun convenio)
    y progreso s sobre el circuito."""
    d2 = ((PTS - p) ** 2).sum(axis=1)
    i = int(d2.argmin())
    delta = p - PTS[i]
    t = TGT[i]
    # componente lateral con signo (convenio CapyTown):
    # robot a la IZQUIERDA del eje -> carril a su derecha -> e > 0
    e = delta[1] * t[0] - delta[0] * t[1]
    return e, S_DENSO[i]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--kp", type=float, default=2.5)
    ap.add_argument("--ki", type=float, default=0.0)
    ap.add_argument("--kd", type=float, default=0.3)
    ap.add_argument("--v", type=float, default=0.20, help="velocidad lineal (m/s)")
    ap.add_argument("--vueltas", type=int, default=3)
    ap.add_argument("--look", type=float, default=0.15, help="distancia look-ahead (m)")
    ap.add_argument("--ruido", type=float, default=0.0, help="ruido de medicion (m)")
    a = ap.parse_args()

    dt, tau, max_w, i_lim = 1.0 / 30.0, 0.15, 2.0, 0.5
    rng = np.random.default_rng(11)
    # estado inicial: sobre la recta inferior, 5 cm desviado
    x, y, th, w = 0.0, 0.05, 0.0, 0.0
    integral, e_prev = 0.0, None
    T, E, XS, YS = [], [], [], []
    s_prev, s_acc, t_vuelta, tiempos = 0.0, 0.0, 0.0, []
    t = 0.0
    while len(tiempos) < a.vueltas and t < 600:
        # medicion en el punto look-ahead (lo que "ve" la camara)
        pla = np.array([x + a.look * math.cos(th), y + a.look * math.sin(th)])
        e, s_now = error_lateral(pla)
        e += rng.normal(0.0, a.ruido)
        # --- PID identico al nodo (con el signo del convenio) ---
        integral = max(-i_lim, min(i_lim, integral + e * dt))
        d = 0.0 if e_prev is None else (e - e_prev) / dt
        e_prev = e
        w_cmd = -(a.kp * e + a.ki * integral + a.kd * d)
        w_cmd = max(-max_w, min(max_w, w_cmd))
        w += (w_cmd - w) * dt / tau
        # cinematica
        x += a.v * math.cos(th) * dt
        y += a.v * math.sin(th) * dt
        th += w * dt
        # progreso / conteo de vueltas
        ds = (s_now - s_prev) % PERIM
        if ds < 0.05:                  # avance fisicamente plausible en un paso
            s_acc += ds
        s_prev = s_now
        t_vuelta += dt
        if s_acc >= PERIM:
            s_acc -= PERIM
            tiempos.append(t_vuelta)
            t_vuelta = 0.0
        T.append(t); E.append(e); XS.append(x); YS.append(y)
        t += dt

    E = np.array(E)
    fuera = (np.abs(E) > LANE_HALF).any()
    print(f"ganancias        : kp={a.kp} ki={a.ki} kd={a.kd}  v={a.v} m/s  look={a.look} m")
    print(f"vueltas completas: {len(tiempos)} / {a.vueltas}" + ("" if len(tiempos) == a.vueltas else "  (se acabo el tiempo!)"))
    for i, tv in enumerate(tiempos, 1):
        print(f"  vuelta {i}: {tv:5.1f} s")
    print(f"|error| medio    : {np.abs(E).mean()*100:.2f} cm   (rubrica: <= 3 cm)")
    print(f"|error| maximo   : {np.abs(E).max()*100:.2f} cm   (medio carril = {LANE_HALF*100:.1f} cm)")
    print("SE SALIO DEL JIRON" if fuera else "se mantuvo dentro del jiron")
    if np.abs(E).mean() > 0.03:
        print("pista: en curva, un P puro necesita error para sostener omega = v/R.")
        print("       sube kp (y kd para amortiguar) o anade ki - el sesgo sostenido")
        print("       en curvas es justo lo que elimina el termino integral.")

    fig, ax = plt.subplots(figsize=(7, 6))
    borde_i = PTS + np.column_stack([-TGT[:, 1], TGT[:, 0]]) * LANE_HALF
    borde_d = PTS - np.column_stack([-TGT[:, 1], TGT[:, 0]]) * LANE_HALF
    ax.plot(PTS[:, 0], PTS[:, 1], "--", c="#C49000", lw=1, label="eje amarillo")
    ax.plot(borde_i[:, 0], borde_i[:, 1], c="gray", lw=1)
    ax.plot(borde_d[:, 0], borde_d[:, 1], c="gray", lw=1, label="bordes")
    ax.plot(XS, YS, c="#2E8B57", lw=1.5, label="chaski")
    ax.set_aspect("equal"); ax.legend(); ax.grid(alpha=0.3)
    ax.set_title(f"Trayectoria - kp={a.kp} ki={a.ki} kd={a.kd}")
    fig.tight_layout(); fig.savefig("lane_sim_trayectoria.png", dpi=130)

    fig2, ax2 = plt.subplots(figsize=(9, 3.5))
    ax2.plot(T, np.array(E) * 100, c="#C49000", lw=1)
    ax2.axhline(0, ls="--", c="gray")
    ax2.axhspan(-3, 3, color="green", alpha=0.08, label="rubrica +-3 cm")
    ax2.set_xlabel("tiempo (s)"); ax2.set_ylabel("/lane_error (cm)")
    ax2.set_title("Error lateral simulado"); ax2.grid(alpha=0.3); ax2.legend()
    fig2.tight_layout(); fig2.savefig("lane_sim_error.png", dpi=130)
    print("graficas: lane_sim_trayectoria.png, lane_sim_error.png")


if __name__ == "__main__":
    main()
