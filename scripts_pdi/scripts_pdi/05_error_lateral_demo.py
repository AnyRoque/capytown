#!/usr/bin/env python3
"""CapyTown scripts_pdi/05 — Del centroide al error lateral (Ejemplo trabajado 3).

Genera una vista de pajaro sintetica y calcula, igual que lane_detector.py:
mascaras HSV -> centroides en la fila de muestreo -> centro del carril ->
error en metros. Reproduce los 3 casos de la clase:
  A) se ven ambas lineas   B) solo el eje amarillo   C) ninguna linea (NaN)

Uso:  python3 05_error_lateral_demo.py
"""
import numpy as np
import cv2

W, H = 640, 480
PX_PER_M = 600.0
LANE_W_M = 0.21
LOOK_ROW = 0.6
WHITE_LO, WHITE_HI = np.array([0, 0, 180]), np.array([180, 30, 255])
YELLOW_LO, YELLOW_HI = np.array([20, 100, 100]), np.array([35, 255, 255])


def escena(x_yellow=None, x_white=None):
    img = np.full((H, W, 3), (35, 35, 35), np.uint8)
    if x_yellow is not None:
        for y0 in range(0, H, 80):
            cv2.rectangle(img, (x_yellow - 8, y0), (x_yellow + 8, y0 + 48), (40, 200, 220), -1)
    if x_white is not None:
        cv2.rectangle(img, (x_white - 8, 0), (x_white + 8, H), (205, 210, 200), -1)
    return img


def centroide_x(mask):
    m = cv2.moments(mask, binaryImage=True)
    return None if m["m00"] < 1e-3 else m["m10"] / m["m00"]


def medir(img, nombre):
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    mw = cv2.inRange(hsv, WHITE_LO, WHITE_HI)
    my = cv2.inRange(hsv, YELLOW_LO, YELLOW_HI)
    row = int(LOOK_ROW * H)
    banda = slice(max(0, row - 8), min(H, row + 8))
    xw, xy = centroide_x(mw[banda, :]), centroide_x(my[banda, :])

    half_px = (LANE_W_M / 2.0) * PX_PER_M
    if xw is not None and xy is not None:
        centro = (xw + xy) / 2.0
    elif xy is not None:
        centro = xy + half_px          # solo eje amarillo: carril a su derecha
    elif xw is not None:
        centro = xw - half_px          # solo borde blanco: carril a su izquierda
    else:
        centro = None
    error_m = float("nan") if centro is None else (centro - W / 2.0) / PX_PER_M

    cx = "None" if centro is None else f"{centro:6.1f}"
    xw_s = " None" if xw is None else f"{xw:5.0f}"
    xy_s = " None" if xy is None else f"{xy:5.0f}"
    print(f"{nombre:<28} | x_amar={xy_s} | x_blanco={xw_s} | centro={cx} px | e = {error_m:+.3f} m")

    dbg = img.copy()
    cv2.line(dbg, (0, row), (W, row), (0, 255, 0), 1)
    for x, c in ((xw, (255, 255, 255)), (xy, (0, 255, 255)), (centro, (0, 0, 255))):
        if x is not None:
            cv2.circle(dbg, (int(x), row), 7, c, -1)
    cv2.line(dbg, (W // 2, row - 25), (W // 2, row + 25), (200, 120, 0), 2)  # centro robot
    return dbg


print(f"convenio: e > 0 -> carril a la DERECHA del robot -> girar a la derecha (w < 0)")
print(f"params  : px_per_meter={PX_PER_M}  lane_width={LANE_W_M} m  centro robot = px {W//2}")
print("-" * 100)
casos = [
    ("Caso A: ambas lineas", escena(x_yellow=180, x_white=420)),
    ("Caso B: solo eje amarillo", escena(x_yellow=260)),
    ("Caso C: ninguna linea", escena()),
]
paneles = [medir(img, nombre) for nombre, img in casos]
cv2.imwrite("error_lateral_demo.png", np.hstack(paneles))
print("-" * 100)
print("guardado: error_lateral_demo.png (A | B | C; punto rojo = centro del carril estimado)")
print("Caso C produce NaN: el lane_controller debe frenar por timeout, no asumir 0.")
