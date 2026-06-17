#!/usr/bin/env python3
"""ipm_picker.py — Selector de los 4 puntos del trapecio para la IPM (CapyTown).

Complemento del PPTX y la guia. La vista de pajaro (Inverse Perspective Mapping)
necesita 4 puntos del piso en la imagen de la camara. Este script te deja hacer
clic sobre ellos y te imprime las coordenadas NORMALIZADAS listas para pegar en
`build_ipm()` de lane_detector.py.

Uso:
    python3 ipm_picker.py --source pista.jpg
    python3 ipm_picker.py --source 0          # camara

Orden de clics (importante):
    1. Superior-izquierda   2. Superior-derecha
    3. Inferior-derecha     4. Inferior-izquierda

Teclas:
    - 'r'  reinicia los puntos
    - 'p'  previsualiza la vista de pajaro con los puntos actuales
    - 'q'  / ESC  salir
"""
import argparse
import cv2
import numpy as np

WIN = "IPM Picker — clic 4 puntos (TL, TR, BR, BL)"
pts = []


def on_mouse(event, x, y, flags, param):
    if event == cv2.EVENT_LBUTTONDOWN and len(pts) < 4:
        pts.append((x, y))


def grab(cap, static):
    if static is not None:
        return static.copy()
    ok, f = cap.read()
    return f if ok else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default="0")
    ap.add_argument("--width", type=int, default=640)
    ap.add_argument("--height", type=int, default=480)
    args = ap.parse_args()

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

    cv2.namedWindow(WIN)
    cv2.setMouseCallback(WIN, on_mouse)
    print("[ipm_picker] Clic en orden: TL, TR, BR, BL. 'p' previsualiza, 'r' reinicia.")

    while True:
        frame = grab(cap, static)
        if frame is None:
            break
        frame = cv2.resize(frame, (args.width, args.height))
        h, w = frame.shape[:2]
        for i, (x, y) in enumerate(pts):
            cv2.circle(frame, (x, y), 6, (0, 0, 255), -1)
            cv2.putText(frame, str(i + 1), (x + 8, y),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
        if len(pts) == 4:
            cv2.polylines(frame, [np.array(pts, np.int32)], True, (0, 255, 0), 2)
        cv2.imshow(WIN, frame)

        k = cv2.waitKey(30) & 0xFF
        if k in (ord('q'), 27):
            break
        elif k == ord('r'):
            pts.clear()
        elif k == ord('p') and len(pts) == 4:
            src = np.float32(pts)
            dst = np.float32([[0.30 * w, 0], [0.70 * w, 0],
                              [0.70 * w, h], [0.30 * w, h]])
            M = cv2.getPerspectiveTransform(src, dst)
            warp = cv2.warpPerspective(frame, M, (w, h))
            cv2.imshow("Vista de pajaro (preview)", warp)
            print_normalized(pts, w, h)

    if len(pts) == 4:
        print_normalized(pts, args.width, args.height)
    if cap is not None:
        cap.release()
    cv2.destroyAllWindows()


def print_normalized(points, w, h):
    print("\n[ipm_picker] Pega esto en build_ipm() de lane_detector.py:\n")
    print("        src = np.float32([")
    labels = ["TL", "TR", "BR", "BL"]
    for (x, y), lab in zip(points, labels):
        print(f"            [{x / w:.2f} * w, {y / h:.2f} * h],   # {lab}")
    print("        ])")
    print("        dst = np.float32([[0.30*w, 0], [0.70*w, 0],")
    print("                          [0.70*w, h], [0.30*w, h]])\n")


if __name__ == "__main__":
    main()
