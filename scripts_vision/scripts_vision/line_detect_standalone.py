#!/usr/bin/env python3
"""line_detect_standalone.py — Pipeline de deteccion de linea SIN ROS (CapyTown).

Reproduce, en un solo archivo y sin necesidad de ROS2, exactamente la logica del
nodo `lane_detector`: IPM -> HSV -> mascara -> centroide -> error lateral.
Sirve para que el alumno experimente la deteccion en su laptop antes de pasar al
robot. Es el complemento practico del PPTX «Percepcion Visual y Deteccion de
Lineas Blancas».

Uso:
    python3 line_detect_standalone.py --source 0            # camara
    python3 line_detect_standalone.py --source pista.mp4    # video
    python3 line_detect_standalone.py --source pista.jpg --params hsv_params.yaml

Salida: ventana de depuracion con la vista de pajaro, la fila look-ahead, los
centroides (blanco/amarillo/centro) y el error lateral impreso en metros.
"""
import argparse
import cv2
import numpy as np

# --- Parametros por defecto (espejo de config/hsv_params.yaml) ---
DEFAULTS = dict(
    white_lo=(0, 0, 180),     white_hi=(180, 30, 255),
    yellow_lo=(20, 100, 100), yellow_hi=(35, 255, 255),
    min_area=150, lane_width_m=0.21, px_per_meter=600.0,
    look_ahead_row=0.6,
)


def load_params(path):
    """Carga umbrales desde un hsv_params.yaml (sin dependencia de PyYAML)."""
    p = dict(DEFAULTS)
    if not path:
        return p
    vals = {}
    for line in open(path):
        line = line.split("#")[0].strip()
        if ":" in line:
            k, _, v = line.partition(":")
            v = v.strip()
            try:
                vals[k.strip()] = float(v)
            except ValueError:
                pass
    g = lambda k, d: int(vals.get(k, d))
    if "white_h_min" in vals:
        p["white_lo"] = (g("white_h_min", 0), g("white_s_min", 0), g("white_v_min", 180))
        p["white_hi"] = (g("white_h_max", 180), g("white_s_max", 30), g("white_v_max", 255))
        p["yellow_lo"] = (g("yellow_h_min", 20), g("yellow_s_min", 100), g("yellow_v_min", 100))
        p["yellow_hi"] = (g("yellow_h_max", 35), g("yellow_s_max", 255), g("yellow_v_max", 255))
    for k in ("min_area", "lane_width_m", "px_per_meter", "look_ahead_row"):
        if k in vals:
            p[k] = vals[k]
    return p


def build_ipm(w, h):
    src = np.float32([[0.18 * w, 0.62 * h], [0.82 * w, 0.62 * h],
                      [1.00 * w, 0.98 * h], [0.00 * w, 0.98 * h]])
    dst = np.float32([[0.30 * w, 0], [0.70 * w, 0],
                      [0.70 * w, h], [0.30 * w, h]])
    return cv2.getPerspectiveTransform(src, dst)


def centroid_x(mask):
    m = cv2.moments(mask, binaryImage=True)
    if m["m00"] < 1e-3:
        return None
    return m["m10"] / m["m00"]


def process(frame, P, M):
    h, w = frame.shape[:2]
    warp = cv2.warpPerspective(frame, M, (w, h))
    hsv = cv2.cvtColor(warp, cv2.COLOR_BGR2HSV)
    k = np.ones((3, 3), np.uint8)
    mw = cv2.morphologyEx(cv2.inRange(hsv, np.array(P["white_lo"]),  np.array(P["white_hi"])),  cv2.MORPH_OPEN, k)
    my = cv2.morphologyEx(cv2.inRange(hsv, np.array(P["yellow_lo"]), np.array(P["yellow_hi"])), cv2.MORPH_OPEN, k)

    row = int(P["look_ahead_row"] * h)
    band = slice(max(0, row - 8), min(h, row + 8))
    xw = centroid_x(mw[band, :])
    xy = centroid_x(my[band, :])

    half = (P["lane_width_m"] / 2.0) * P["px_per_meter"]
    if xw is not None and xy is not None:
        center = (xw + xy) / 2.0
    elif xy is not None:
        center = xy + half
    elif xw is not None:
        center = xw - half
    else:
        center = None
    error_m = float("nan") if center is None else (center - w / 2.0) / P["px_per_meter"]

    dbg = warp.copy()
    cv2.line(dbg, (0, row), (w, row), (0, 255, 0), 1)
    for x, color in ((xw, (255, 255, 255)), (xy, (0, 255, 255)), (center, (0, 0, 255))):
        if x is not None:
            cv2.circle(dbg, (int(x), row), 6, color, -1)
    txt = "error = NaN (sin deteccion)" if center is None else f"error = {error_m:+.3f} m"
    cv2.putText(dbg, txt, (10, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
    mask_view = cv2.cvtColor(cv2.bitwise_or(mw, my), cv2.COLOR_GRAY2BGR)
    return error_m, np.hstack([dbg, mask_view])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default="0")
    ap.add_argument("--params", default=None, help="hsv_params.yaml opcional")
    args = ap.parse_args()
    P = load_params(args.params)

    static, cap = None, None
    if args.source.isdigit():
        cap = cv2.VideoCapture(int(args.source))
    else:
        img = cv2.imread(args.source)
        static = img if img is not None else None
        if static is None:
            cap = cv2.VideoCapture(args.source)
    if static is None and (cap is None or not cap.isOpened()):
        raise SystemExit(f"No pude abrir: {args.source}")

    M = None
    print("[line_detect] 'q'/ESC para salir.")
    while True:
        frame = static.copy() if static is not None else (cap.read()[1] if cap else None)
        if frame is None:
            break
        frame = cv2.resize(frame, (640, 480))
        if M is None:
            M = build_ipm(640, 480)
        err, view = process(frame, P, M)
        cv2.imshow("Deteccion de linea (vista pajaro | mascara)", view)
        if cv2.waitKey(30) & 0xFF in (ord('q'), 27):
            break
    if cap is not None:
        cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
