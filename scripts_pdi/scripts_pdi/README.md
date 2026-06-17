# scripts_pdi — Scripts de apoyo a la clase RC-2 "Las 3 Vueltas del Jirón"

Material de práctica **sin robot** para la Semana 11 (control PID: del giroscopio
a la cámara). Cada script acompaña una sección de la clase
`CapyTown_Semana11_RC2_Clase-FINA.pptx`.

## Requisitos

```bash
pip install numpy matplotlib opencv-python
# 07 requiere ademas ROS2 Humble (solo en el Pi5 / VM del curso)
```

## Mapa script ↔ clase

| Script | Diapositiva / momento | Qué hace |
|---|---|---|
| `core_pid.py` | (módulo común) | Simulador de rumbo: uniciclo + retardo de actuador + PID con anti-windup y saturación. |
| `01_pid_simulador.py` | Bloque 1 · Experimentos 1 y 2 · Ejemplo trabajado 1 | `--modo recto` (perturbación) o `--modo giro90` (escalón). `--paso-a-paso` reproduce el cálculo a mano de la clase. Métricas: sobreimpulso, asentamiento, error final. |
| `02_comparador_ganancias.py` | Bloque 1 · "Tu laboratorio de bolsillo" | Barre **un** parámetro (kp/ki/kd) con los demás fijos y superpone las curvas — la regla TPACK hecha script. |
| `heading_controller.py` | Bloque 1 · Experimento 1 "Camina recto, chaski" (diapositiva 7) | **Nodo ROS2** (no simulador): suscribe `/odom`, fija el setpoint = yaw inicial θ₀, corre el PID y publica `/cmd_vel` (v=0.20 m/s). Mismo esqueleto PID que luego reutiliza `lane_controller.py` con `/lane_error`. Requiere ROS2 Humble (Pi5/VM). |
| `03_hsv_explorador.py` | Bloque 2 · HSV · Ejemplo trabajado 2 | `--pixel B G R` clasifica un píxel (amarillo/blanco/fondo). `--gui` abre el tuner de barras. Sin args: máscaras sobre imagen sintética. |
| `04_ipm_demo.py` | Bloque 2 · IPM | Aplica la homografía de `lane_detector.py` a una escena en perspectiva y guarda el lado-a-lado. Verifica que las líneas queden rectas y verticales. |
| `05_error_lateral_demo.py` | Bloque 2 · Ejemplo trabajado 3 | Reproduce los casos A (ambas líneas), B (solo amarillo) y C (ninguna → NaN) con los números exactos de la diapositiva. |
| `06_lane_sim.py` | Bloque 3 · "Simulador de lane following" | Circuito estadio a escala del Tambo, 3 vueltas, curva de `/lane_error` y métricas de la rúbrica. Para sintonizar mientras esperas tu turno de pista. |
| `07_plot_lane_error.py` | Bloque 4 · Evidencia / entregable | Genera `lane_error_s11.png` desde el `ros2 bag` y calcula el \|error\| medio (criterio ≤ 3 cm). |

## Flujo sugerido (antes del lab)

```bash
python3 01_pid_simulador.py --paso-a-paso              # el ejemplo de la clase
python3 01_pid_simulador.py --modo giro90 --kp 2.0     # solo P
python3 01_pid_simulador.py --modo giro90 --kp 2.0 --kd 0.4   # P+D
python3 02_comparador_ganancias.py --param kp --valores 0.8 2.5 6.0
python3 03_hsv_explorador.py --pixel 40 200 220
python3 04_ipm_demo.py
python3 05_error_lateral_demo.py
python3 06_lane_sim.py --kp 2.5 --kd 0.3 --vueltas 3
```

## Reto de sintonización (06_lane_sim)

Con las ganancias por defecto (`--kp 2.5 --kd 0.3`) el chaski **se sale en las
curvas**: un P puro necesita error para sostener ω = v/R (sesgo sostenido).
Tu misión, igual que en la pista: lograr |error| medio ≤ 3 cm cambiando
**un parámetro a la vez**. Pista: sube Kp (con Kd para amortiguar) y remata
el sesgo de curva con un Ki pequeño.

Regla de oro (igual que en la pista): **un parámetro por prueba**, compara
las curvas antes y después, anota qué cambió.

*Universidad ESAN · Robótica 2026-I · CapyTown · Prof. Marks Calderón Niquin*
