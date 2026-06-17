#!/usr/bin/env python3
"""CapyTown scripts_pdi/01 — Simulador PID de rumbo (sin robot).

Soporta los dos experimentos del Bloque 1 de la clase:
  --modo recto   Experimento 1: mantener rumbo tras una perturbacion de 12 deg.
  --modo giro90  Experimento 2: respuesta al escalon de 90 deg.
  --paso-a-paso  Reproduce el Ejemplo trabajado 1 de la clase (una iteracion a mano).

Uso tipico (un parametro a la vez, como en el lab):
  python3 01_pid_simulador.py --modo giro90 --kp 2.0
  python3 01_pid_simulador.py --modo giro90 --kp 2.0 --kd 0.4
"""
import argparse
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from core_pid import simular, metricas


def paso_a_paso():
    kp, ki, kd, dt = 2.5, 0.0, 0.3, 1.0 / 30.0
    e, e_prev, integral = 0.04, 0.06, 0.0
    print("Ejemplo trabajado 1 (diapositiva 'Una iteracion del PID, a mano')")
    print(f"  datos : kp={kp}  ki={ki}  kd={kd}  e={e} rad  e_prev={e_prev} rad  dt=1/30 s")
    P = kp * e
    integral += e * dt
    I = ki * integral
    D = kd * (e - e_prev) / dt
    w = -(P + I + D)
    print(f"  P = kp*e            = {P:+.3f}")
    print(f"  I = ki*integral     = {I:+.3f}")
    print(f"  D = kd*(e-e_prev)/dt= {D:+.3f}")
    print(f"  w = -(P+I+D)        = {w:+.3f} rad/s")
    print("  Lectura: el error cae rapido -> D supera a P y frena la correccion (amortiguamiento).")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--kp", type=float, default=2.5)
    ap.add_argument("--ki", type=float, default=0.0)
    ap.add_argument("--kd", type=float, default=0.0)
    ap.add_argument("--modo", choices=["recto", "giro90"], default="giro90")
    ap.add_argument("--ruido", type=float, default=0.0, help="desv. std del ruido de medicion (rad)")
    ap.add_argument("--t", type=float, default=6.0, help="duracion (s)")
    ap.add_argument("--paso-a-paso", action="store_true", help="ejemplo numerico de la clase y salir")
    a = ap.parse_args()

    if a.paso_a_paso:
        paso_a_paso()
        return

    sim = simular(a.kp, a.ki, a.kd, modo=a.modo, t_fin=a.t, ruido=a.ruido)
    m = metricas(sim)

    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.plot(sim["t"], sim["yaw_deg"], lw=2, color="#C49000",
            label=f"yaw  (kp={a.kp} ki={a.ki} kd={a.kd})")
    ax.axhline(sim["setpoint_deg"], ls="--", c="gray", label="setpoint")
    if a.modo == "giro90":
        ax.axhspan(88, 92, color="green", alpha=0.08, label="banda +-2 deg")
    ax.set_xlabel("tiempo (s)"); ax.set_ylabel("yaw (deg)")
    ax.set_title(f"CapyTown RC-2 - simulador de rumbo ({a.modo})")
    ax.grid(alpha=0.3); ax.legend()
    out = f"pid_{a.modo}_kp{a.kp}_ki{a.ki}_kd{a.kd}.png"
    fig.tight_layout(); fig.savefig(out, dpi=130)

    print(f"grafica  : {out}")
    print(f"sobreimpulso     : {m['sobreimpulso_pct']:.1f} %")
    ta = m["t_asentamiento_s"]
    print(f"t asentamiento   : {ta:.2f} s" if ta is not None else "t asentamiento   : NO se asienta (inestable u oscilando)")
    print(f"error final      : {m['error_final_deg']:.2f} deg")


if __name__ == "__main__":
    main()
