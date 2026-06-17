#!/usr/bin/env python3
"""hsv_tuner.py — Calibrador interactivo de rangos HSV (CapyTown).

Complemento del PPTX «Percepción Visual y Detección de Líneas Blancas» y de la
guía de laboratorio. Sirve para encontrar los 6 umbrales HSV de la línea BLANCA
(borde) y del eje AMARILLO antes de lanzar el nodo `lane_detector`.

Uso:
    # Desde una cámara (índice 0 por defecto)
    python3 hsv_tuner.py --source 0

    # Desde una imagen o un video
    python3 hsv_tuner.py --source pista.jpg
    python3 hsv_tuner.py --source pista.mp4

Controles:
    - Mueve los trackbars hasta que SOLO la línea quede blanca en la máscara.
    - Tecla 'w'  -> editas el color BLANCO   (white)
    - Tecla 'y'  -> editas el color AMARILLO  (yellow)
    - Tecla 's'  -> guarda los rangos actuales en hsv_params.yaml
    - Tecla 'q' / ESC -> salir

El YAML generado es compatible con config/hsv_params.yaml del paquete
capytown_esan_pkg.
"""
import argparse
import cv2
import numpy as np

WIN = "HSV Tuner — CapyTown"
MASK = "Mascara"

# Valores iniciales (los mismos del repo)
PRESETS = {
    "white":  dict(h_min=0,  h_max=180, s_min=0,   s_max=30,  v_min=180, v_max=255),
    "yellow": dict(h_min=20, h_max=35,  s_min=100, s_max=255, v_min=100, v_max=255),
}


def nothing(_):
    pass


def make_trackbars(values):
    cv2.namedWindow(WIN, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(WIN, 420, 320)
    for name, maxv in (("H min", 180), ("H max", 180), ("S min", 255),
                       ("S max", 255), ("V min", 255), ("V max", 255)):
        cv2.createTrackbar(name, WIN, 0, maxv, nothing)
    set_trackbars(values)


def set_trackbars(v):
    cv2.setTrackbarPos("H min", WIN, v["h_min"])
    cv2.setTrackbarPos("H max", WIN, v["h_max"])
    cv2.setTrackbarPos("S min", WIN, v["s_min"])
    cv2.setTrackbarPos("S max", WIN, v["s_max"])
    cv2.setTrackbarPos("V min", WIN, v["v_min"])
    cv2.setTrackbarPos("V max", WIN, v["v_max"])


def read_trackbars():
    g = lambda n: cv2.getTrackbarPos(n, WIN)
    return dict(h_min=g("H min"), h_max=g("H max"), s_min=g("S min"),
                s_max=g("S max"), v_min=g("V min"), v_max=g("V max"))


def save_yaml(white, yellow, path="hsv_params.yaml"):
    txt = f"""# CapyTown — Rangos HSV calibrados con hsv_tuner.py
lane_detector:
  ros__parameters:
    # Blanco — borde del carril
    white_h_min: {white['h_min']}
    white_h_max: {white['h_max']}
    white_s_min: {white['s_min']}
    white_s_max: {white['s_max']}
    white_v_min: {white['v_min']}
    white_v_max: {white['v_max']}
    # Amarillo — eje central
    yellow_h_min: {yellow['h_min']}
    yellow_h_max: {yellow['h_max']}
    yellow_s_min: {yellow['s_min']}
    yellow_s_max: {yellow['s_max']}
    yellow_v_min: {yellow['v_min']}
    yellow_v_max: {yellow['v_max']}
    # Geometria / IPM (ajustar manualmente)
    min_area: 150
    lane_width_m: 0.21
    px_per_meter: 600.0
    look_ahead_row: 0.6
    publish_debug: true
"""
    with open(path, "w") as f:
        f.write(txt)
    print(f"[hsv_tuner] Guardado en {path}")


def get_frame(cap, static_img):
    if static_img is not None:
        return static_img.copy()
    ok, frame = cap.read()
    if not ok:
        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)  # rebobina video
        ok, frame = cap.read()
    return frame if ok else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default="0",
                    help="Indice de camara (0), imagen o video.")
    args = ap.parse_args()

    static_img, cap = None, None
    if args.source.isdigit():
        cap = cv2.VideoCapture(int(args.source))
    else:
        img = cv2.imread(args.source)
        if img is not None:
            static_img = img
        else:
            cap = cv2.VideoCapture(args.source)
    if static_img is None and (cap is None or not cap.isOpened()):
        raise SystemExit(f"No pude abrir la fuente: {args.source}")

    current = "white"
    values = {k: dict(v) for k, v in PRESETS.items()}
    make_trackbars(values[current])
    print("[hsv_tuner] Editando BLANCO. 'w'/'y' cambia color, 's' guarda, 'q' sale.")

    while True:
        frame = get_frame(cap, static_img)
        if frame is None:
            break
        frame = cv2.resize(frame, (640, 480))
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        v = read_trackbars()
        values[current] = v
        lo = np.array([v["h_min"], v["s_min"], v["v_min"]])
        hi = np.array([v["h_max"], v["s_max"], v["v_max"]])
        mask = cv2.inRange(hsv, lo, hi)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
        res = cv2.bitwise_and(frame, frame, mask=mask)

        cv2.putText(frame, f"Editando: {current.upper()}", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
        cv2.imshow(WIN, frame)
        cv2.imshow(MASK, np.hstack([cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR), res]))

        k = cv2.waitKey(30) & 0xFF
        if k in (ord('q'), 27):
            break
        elif k == ord('w'):
            current = "white"; set_trackbars(values[current])
            print("[hsv_tuner] Editando BLANCO")
        elif k == ord('y'):
            current = "yellow"; set_trackbars(values[current])
            print("[hsv_tuner] Editando AMARILLO")
        elif k == ord('s'):
            save_yaml(values["white"], values["yellow"])

    if cap is not None:
        cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
