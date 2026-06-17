#!/usr/bin/env python3
"""make_test_track.py — Genera una pista sintetica para probar la deteccion.

Crea una imagen (y opcionalmente un video) con el aspecto de la vista frontal de
CapyTown: asfalto gris, borde BLANCO y eje central AMARILLO discontinuo, en
perspectiva. Util para probar hsv_tuner.py y line_detect_standalone.py SIN robot.

Uso:
    python3 make_test_track.py                      # crea pista_test.jpg
    python3 make_test_track.py --offset 80          # carril desplazado a la derecha
    python3 make_test_track.py --video 150          # crea pista_test.mp4 (150 frames)
"""
import argparse
import cv2
import numpy as np

W, H = 640, 480


def render(offset=0):
    img = np.full((H, W, 3), 60, np.uint8)            # asfalto
    cx = W // 2 + offset
    # Trapecio en perspectiva: ancho arriba < ancho abajo
    top_y, bot_y = int(0.55 * H), H
    top_half, bot_half = 60, 230

    def edge(sign):
        p_top = (cx + sign * top_half, top_y)
        p_bot = (cx + sign * bot_half, bot_y)
        cv2.line(img, p_top, p_bot, (255, 255, 255), 6)   # borde blanco

    edge(-1)
    edge(+1)
    # Eje amarillo discontinuo (centro)
    n = 8
    for i in range(n):
        t0 = i / n
        t1 = t0 + 0.5 / n
        y0 = int(top_y + t0 * (bot_y - top_y))
        y1 = int(top_y + t1 * (bot_y - top_y))
        cv2.line(img, (cx, y0), (cx, y1), (0, 220, 220), 5)
    # Cielo / fondo arriba
    cv2.rectangle(img, (0, 0), (W, top_y), (90, 70, 50), -1)
    return img


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--offset", type=int, default=0,
                    help="Desplazamiento del carril en px (simula error lateral).")
    ap.add_argument("--video", type=int, default=0,
                    help="Si > 0, genera un video con ese numero de frames.")
    args = ap.parse_args()

    if args.video > 0:
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        out = cv2.VideoWriter("pista_test.mp4", fourcc, 30, (W, H))
        for i in range(args.video):
            off = int(120 * np.sin(2 * np.pi * i / args.video))  # serpentea
            out.write(render(off))
        out.release()
        print("[make_test_track] pista_test.mp4 generado.")
    else:
        cv2.imwrite("pista_test.jpg", render(args.offset))
        print("[make_test_track] pista_test.jpg generado.")


if __name__ == "__main__":
    main()
