#!/usr/bin/env python3
"""CapyTown scripts_pdi/03 — Explorador HSV.

Tres modos:
  --pixel B G R      Clasifica un pixel (reproduce el Ejemplo trabajado 2 de la clase).
  --imagen ruta      Aplica los rangos del lab a una imagen y guarda las mascaras.
  --gui [ruta]       Tuner interactivo con barras (igual al hsv_tuner del lab).
  (sin argumentos)   Genera una imagen sintetica de carril y guarda las mascaras.

Ejemplos:
  python3 03_hsv_explorador.py --pixel 40 200 220
  python3 03_hsv_explorador.py --imagen foto_pista.jpg
"""
import argparse
import numpy as np
import cv2

# Rangos por defecto = hsv_params.yaml de la clase (recalibrar el dia del lab)
WHITE_LO, WHITE_HI = np.array([0, 0, 180]), np.array([180, 30, 255])
YELLOW_LO, YELLOW_HI = np.array([20, 100, 100]), np.array([35, 255, 255])


def clasificar_pixel(b, g, r):
    px = np.uint8([[[b, g, r]]])
    h, s, v = cv2.cvtColor(px, cv2.COLOR_BGR2HSV)[0, 0]
    print(f"BGR ({b}, {g}, {r})  ->  HSV ({h}, {s}, {v})")
    es_blanco = WHITE_LO[1] <= s <= WHITE_HI[1] and WHITE_LO[2] <= v <= WHITE_HI[2]
    es_amar = (YELLOW_LO[0] <= h <= YELLOW_HI[0] and s >= YELLOW_LO[1] and v >= YELLOW_LO[2])
    if es_amar:
        print("-> AMARILLO (eje central): H en [20,35], S>=100, V>=100")
    elif es_blanco:
        print("-> BLANCO (borde derecho): S<=30, V>=180")
    else:
        print("-> FONDO / otro: no cumple ningun rango")


def imagen_sintetica(w=640, h=480):
    """Vista de pajaro sintetica: cartulina negra + eje amarillo + borde blanco."""
    img = np.full((h, w, 3), (35, 35, 35), np.uint8)
    ruido = np.random.default_rng(3).integers(-10, 10, (h, w, 1))
    img = np.clip(img.astype(int) + ruido, 0, 255).astype(np.uint8)
    for y0 in range(0, h, 80):                      # eje amarillo discontinuo
        cv2.rectangle(img, (172, y0), (188, y0 + 48), (40, 200, 220), -1)
    cv2.rectangle(img, (412, 0), (428, h), (205, 210, 200), -1)  # borde blanco
    return img


def procesar(img, etiqueta="img"):
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    mw = cv2.inRange(hsv, WHITE_LO, WHITE_HI)
    my = cv2.inRange(hsv, YELLOW_LO, YELLOW_HI)
    k = np.ones((3, 3), np.uint8)
    mw = cv2.morphologyEx(mw, cv2.MORPH_OPEN, k)
    my = cv2.morphologyEx(my, cv2.MORPH_OPEN, k)
    cv2.imwrite(f"hsv_{etiqueta}_original.png", img)
    cv2.imwrite(f"hsv_{etiqueta}_mask_blanco.png", mw)
    cv2.imwrite(f"hsv_{etiqueta}_mask_amarillo.png", my)
    print(f"guardado: hsv_{etiqueta}_original.png + mascaras blanco/amarillo")
    print(f"pixeles blanco: {int((mw > 0).sum())}  |  amarillo: {int((my > 0).sum())}")


def gui(ruta=None):
    img = cv2.imread(ruta) if ruta else imagen_sintetica()
    if img is None:
        raise SystemExit(f"no pude abrir {ruta}")
    win = "hsv_tuner  (q para salir e imprimir YAML)"
    cv2.namedWindow(win)
    bars = [("H min", 20, 180), ("H max", 35, 180), ("S min", 100, 255),
            ("S max", 255, 255), ("V min", 100, 255), ("V max", 255, 255)]
    for n, v0, vmax in bars:
        cv2.createTrackbar(n, win, v0, vmax, lambda x: None)
    while True:
        lo = np.array([cv2.getTrackbarPos("H min", win), cv2.getTrackbarPos("S min", win), cv2.getTrackbarPos("V min", win)])
        hi = np.array([cv2.getTrackbarPos("H max", win), cv2.getTrackbarPos("S max", win), cv2.getTrackbarPos("V max", win)])
        mask = cv2.inRange(cv2.cvtColor(img, cv2.COLOR_BGR2HSV), lo, hi)
        cv2.imshow(win, np.hstack([img, cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR)]))
        if cv2.waitKey(30) & 0xFF == ord("q"):
            break
    cv2.destroyAllWindows()
    print("# pega esto en hsv_params.yaml:")
    print(f"#   h_min: {lo[0]}\n#   h_max: {hi[0]}\n#   s_min: {lo[1]}\n#   s_max: {hi[1]}\n#   v_min: {lo[2]}\n#   v_max: {hi[2]}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pixel", type=int, nargs=3, metavar=("B", "G", "R"))
    ap.add_argument("--imagen", type=str)
    ap.add_argument("--gui", nargs="?", const="", default=None, metavar="RUTA")
    a = ap.parse_args()
    if a.pixel:
        clasificar_pixel(*a.pixel)
    elif a.gui is not None:
        gui(a.gui or None)
    elif a.imagen:
        img = cv2.imread(a.imagen)
        if img is None:
            raise SystemExit(f"no pude abrir {a.imagen}")
        procesar(img, "foto")
    else:
        procesar(imagen_sintetica(), "sintetica")


if __name__ == "__main__":
    main()
