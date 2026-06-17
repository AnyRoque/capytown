#!/usr/bin/env python3
"""CapyTown scripts_pdi/02 — Comparador de ganancias (UN parametro a la vez).

Regla TPACK del lab: nunca cambies dos ganancias en la misma prueba.
Este script barre UN parametro (kp, ki o kd) manteniendo fijos los demas
y superpone las curvas para comparar.

Uso:
  python3 02_comparador_ganancias.py --param kp --valores 0.8 2.5 6.0
  python3 02_comparador_ganancias.py --param kd --valores 0 0.2 0.5 --kp 2.5
"""
import argparse
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from core_pid import simular, metricas

COLORES = ["#C0392B", "#C49000", "#2E8B57", "#2471A3", "#7D3C98"]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--param", choices=["kp", "ki", "kd"], required=True)
    ap.add_argument("--valores", type=float, nargs="+", required=True)
    ap.add_argument("--kp", type=float, default=2.5)
    ap.add_argument("--ki", type=float, default=0.0)
    ap.add_argument("--kd", type=float, default=0.0)
    ap.add_argument("--modo", choices=["recto", "giro90"], default="giro90")
    a = ap.parse_args()

    base = {"kp": a.kp, "ki": a.ki, "kd": a.kd}
    fig, ax = plt.subplots(figsize=(8, 4.5))
    print(f"barrido de {a.param} con base {base} (modo {a.modo})")
    print(f"{'valor':>8} | {'sobre %':>8} | {'t asent':>8} | {'e final':>8}")
    for i, v in enumerate(a.valores):
        g = dict(base); g[a.param] = v
        sim = simular(g["kp"], g["ki"], g["kd"], modo=a.modo)
        m = metricas(sim)
        ax.plot(sim["t"], sim["yaw_deg"], lw=2, color=COLORES[i % len(COLORES)],
                label=f"{a.param}={v}")
        ta = f"{m['t_asentamiento_s']:.2f} s" if m["t_asentamiento_s"] is not None else "nunca"
        print(f"{v:>8} | {m['sobreimpulso_pct']:>7.1f} | {ta:>8} | {m['error_final_deg']:>6.2f}d")
    ax.axhline(sim["setpoint_deg"], ls="--", c="gray")
    ax.set_xlabel("tiempo (s)"); ax.set_ylabel("yaw (deg)")
    ax.set_title(f"Efecto de {a.param} (los demas fijos) - {a.modo}")
    ax.grid(alpha=0.3); ax.legend()
    out = f"comparativa_{a.param}_{a.modo}.png"
    fig.tight_layout(); fig.savefig(out, dpi=130)
    print(f"grafica: {out}")


if __name__ == "__main__":
    main()
