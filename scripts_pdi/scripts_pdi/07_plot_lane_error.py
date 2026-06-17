#!/usr/bin/env python3
"""CapyTown scripts_pdi/07 — Plot de /lane_error desde un ros2 bag (entregable RC-2).

Uso (en el Pi5 o en una maquina con ROS2 Humble):
  python3 07_plot_lane_error.py <ruta_al_bag>
Genera lane_error_s11.png e imprime el |error| medio (criterio de rubrica).
"""
import sys

try:
    from rosbag2_py import SequentialReader, StorageOptions, ConverterOptions
    from rclpy.serialization import deserialize_message
    from std_msgs.msg import Float32
except ImportError:
    raise SystemExit("Este script necesita ROS2 (rosbag2_py). Ejecutalo en el Pi5 o "
                     "en una maquina con ROS2 Humble: source /opt/ros/humble/setup.bash")

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

if len(sys.argv) < 2:
    raise SystemExit("uso: python3 07_plot_lane_error.py <ruta_bag>")

reader = SequentialReader()
reader.open(StorageOptions(uri=sys.argv[1], storage_id="sqlite3"), ConverterOptions("", ""))
t0, ts, errs = None, [], []
while reader.has_next():
    topic, data, stamp = reader.read_next()
    if topic == "/lane_error":
        t0 = stamp if t0 is None else t0
        ts.append((stamp - t0) * 1e-9)
        errs.append(deserialize_message(data, Float32).data)

if not errs:
    raise SystemExit("el bag no contiene /lane_error - revisa 'ros2 bag info'")

import math
validos = [e for e in errs if not math.isnan(e)]
medio = sum(abs(e) for e in validos) / len(validos)

plt.figure(figsize=(10, 4))
plt.plot(ts, errs, lw=0.9, color="#C49000")
plt.axhline(0, ls="--", c="gray")
plt.axhspan(-0.03, 0.03, color="green", alpha=0.08, label="rubrica +-3 cm")
plt.xlabel("tiempo (s)"); plt.ylabel("/lane_error (m)")
plt.title("Error lateral - 3 vueltas RC-2"); plt.grid(True, alpha=0.3); plt.legend()
plt.tight_layout(); plt.savefig("lane_error_s11.png", dpi=150)
print(f"guardado: lane_error_s11.png")
print(f"|error| medio: {medio*100:.2f} cm  ({'CUMPLE' if medio <= 0.03 else 'NO cumple'} la rubrica de 3 cm)")
print(f"muestras: {len(errs)} ({len(errs)-len(validos)} NaN)")
