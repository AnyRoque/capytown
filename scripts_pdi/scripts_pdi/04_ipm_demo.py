#!/usr/bin/env python3
"""CapyTown scripts_pdi/04 — Demo de IPM (vista de pajaro).

Genera una imagen sintetica del carril visto en perspectiva (como la camara
del chaski), aplica la misma homografia que lane_detector.py y guarda la
comparacion lado a lado. Imprime la matriz H.

Uso:
  python3 04_ipm_demo.py
  python3 04_ipm_demo.py --imagen captura_real.jpg
"""
import argparse
import numpy as np
import cv2

W, H = 640, 480


def escena_perspectiva():
    """Carril recto visto en perspectiva: lineas que convergen al horizonte."""
    img = np.full((H, W, 3), (30, 30, 30), np.uint8)
    horizonte = int(0.45 * H)
    # bordes blancos: de las esquinas inferiores hacia el punto de fuga
    fuga = (W // 2, horizonte)
    cv2.line(img, (40, H - 1), (int(fuga[0] - 60), horizonte + 40), (205, 210, 200), 6)
    cv2.line(img, (W - 40, H - 1), (int(fuga[0] + 60), horizonte + 40), (205, 210, 200), 6)
    # eje amarillo discontinuo hacia la fuga
    for f in np.linspace(0.0, 0.8, 7):
        y1 = int((H - 1) * (1 - f) + (horizonte + 40) * f)
        y2 = y1 - int(28 * (1 - f) + 6)
        x = int((W / 2) * 1.0)
        grosor = max(2, int(10 * (1 - f)))
        cv2.line(img, (x, y1), (x, y2), (40, 200, 220), grosor)
    return img


def build_ipm(w, h):
    """Misma geometria que lane_detector.build_ipm (ajustar src en la pista real)."""
    src = np.float32([[0.18 * w, 0.62 * h], [0.82 * w, 0.62 * h],
                      [1.00 * w, 0.98 * h], [0.00 * w, 0.98 * h]])
    dst = np.float32([[0.30 * w, 0.0], [0.70 * w, 0.0],
                      [0.70 * w, h], [0.30 * w, h]])
    return cv2.getPerspectiveTransform(src, dst), src


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--imagen", type=str, help="usar una captura real en vez de la sintetica")
    a = ap.parse_args()
    img = cv2.imread(a.imagen) if a.imagen else escena_perspectiva()
    if img is None:
        raise SystemExit(f"no pude abrir {a.imagen}")
    h, w = img.shape[:2]
    M, src = build_ipm(w, h)
    warp = cv2.warpPerspective(img, M, (w, h))

    vista = img.copy()
    cv2.polylines(vista, [src.astype(int)], True, (60, 60, 230), 2)  # trapecio src
    lado_a_lado = np.hstack([vista, warp])
    cv2.line(lado_a_lado, (w, 0), (w, h), (90, 90, 90), 2)
    cv2.imwrite("ipm_demo.png", lado_a_lado)

    print("homografia H =")
    print(np.array_str(M, precision=3, suppress_small=True))
    print("guardado: ipm_demo.png  (izq: camara + trapecio src | der: vista de pajaro)")
    print("verificacion del lab: en la vista de pajaro las lineas deben quedar RECTAS y VERTICALES.")
    print("si convergen, reajusta los 4 puntos src sobre las esquinas de un tile.")


if __name__ == "__main__":
    main()
