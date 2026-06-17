#!/usr/bin/env python3
"""canny_edges_demo.py — Deteccion de bordes con Canny, interactiva (CapyTown).

Complemento del PPTX «Percepcion Visual y Deteccion de Lineas Blancas», Bloque 4
(§4.3 de Siegwart): filtrado de imagen, suavizado Gaussiano y deteccion de bordes.
Es el espejo practico de la slide 16 «Deteccion de bordes»: la derivada marca las
transiciones de intensidad; Canny/Sobel son una alternativa (o complemento) al
color para encontrar la linea de la pista.

Idea de la slide:
    suavizar (Gauss)  ->  derivar (Sobel)  ->  Canny encadena ambos pasos y
    ademas aplica supresion no-maxima + histeresis con dos umbrales.

Por que importa en CapyTown: el borde del carril es una transicion brusca
asfalto->linea. Canny la marca aunque la iluminacion cambie el brillo absoluto,
cosa que un umbral fijo de color no siempre tolera.

Uso:
    python3 canny_edges_demo.py --source 0                 # camara
    python3 canny_edges_demo.py --source pista_test.jpg    # imagen
    python3 canny_edges_demo.py --source pista_test.mp4    # video

Controles (trackbars de la ventana «Controles»):
    - Blur    : tamano del kernel Gaussiano (0 = sin suavizar). Reduce ruido
                ANTES de derivar; sin esto Canny detecta bordes falsos.
    - Th1/Th2 : umbrales bajo y alto de la histeresis de Canny.
                Regla practica: Th2 ~ 2x-3x Th1.
    - 'g'  -> alterna ver tambien el gradiente Sobel (magnitud).
    - 's'  -> guarda la vista actual en canny_demo_out.jpg
    - 'q' / ESC -> salir.

No requiere ROS; corre en la laptop. Solo necesita opencv-python y numpy.
"""
import argparse
import cv2
import numpy as np

WIN = "Canny — CapyTown"
CTRL = "Controles"


def nothing(_):
    pass


def sobel_magnitude(gray):
    """Magnitud del gradiente con Sobel, normalizada a 0-255 (para visualizar)."""
    gx = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
    mag = cv2.magnitude(gx, gy)
    return cv2.normalize(mag, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)


def label(img, text):
    cv2.putText(img, text, (10, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.6,
                (0, 255, 0), 2, cv2.LINE_AA)
    return img


def process(frame, blur_k, th1, th2):
    """Pipeline de la slide 16: gris -> Gauss -> Canny."""
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    # El kernel Gaussiano debe ser impar; blur_k=0 significa sin suavizado.
    if blur_k > 0:
        k = blur_k * 2 + 1            # 1->3, 2->5, 3->7 ...
        blurred = cv2.GaussianBlur(gray, (k, k), 0)
    else:
        blurred = gray
    edges = cv2.Canny(blurred, th1, th2)
    return gray, blurred, edges


def make_view(frame, blurred, edges, show_sobel):
    """Mosaico: original | suavizado(gris) | Canny  (+ Sobel opcional)."""
    h, w = edges.shape
    orig = label(frame.copy(), "Original")
    blur_bgr = label(cv2.cvtColor(blurred, cv2.COLOR_GRAY2BGR), "Gauss (gris)")
    edges_bgr = label(cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR), "Canny")
    tiles = [orig, blur_bgr, edges_bgr]
    if show_sobel:
        sob = label(cv2.cvtColor(sobel_magnitude(blurred), cv2.COLOR_GRAY2BGR),
                    "Sobel |grad|")
        tiles.append(sob)
    return np.hstack(tiles)


def main():
    ap = argparse.ArgumentParser(
        description="Demo interactiva de deteccion de bordes con Canny (CapyTown).")
    ap.add_argument("--source", default="0",
                    help="indice de camara (0) o ruta a imagen/video.")
    ap.add_argument("--th1", type=int, default=50, help="umbral bajo inicial.")
    ap.add_argument("--th2", type=int, default=150, help="umbral alto inicial.")
    ap.add_argument("--blur", type=int, default=2,
                    help="suavizado inicial (0=ninguno; k -> kernel 2k+1).")
    ap.add_argument("--width", type=int, default=320,
                    help="ancho al que se reescala cada frame (para el mosaico).")
    args = ap.parse_args()

    # ¿Camara (entero) o archivo?
    src = int(args.source) if args.source.isdigit() else args.source
    is_image = isinstance(src, str) and src.lower().endswith(
        (".jpg", ".jpeg", ".png", ".bmp"))

    cv2.namedWindow(CTRL)
    cv2.createTrackbar("Blur", CTRL, args.blur, 8, nothing)
    cv2.createTrackbar("Th1", CTRL, args.th1, 500, nothing)
    cv2.createTrackbar("Th2", CTRL, args.th2, 500, nothing)
    show_sobel = False

    print(__doc__.split("Uso:")[0])
    print("Controles: Blur / Th1 / Th2 (trackbars) · g=Sobel · s=guardar · q=salir\n")

    cap = None
    still = None
    if is_image:
        still = cv2.imread(src)
        if still is None:
            print(f"No se pudo leer la imagen: {src}")
            return
    else:
        cap = cv2.VideoCapture(src)
        if not cap.isOpened():
            print(f"No se pudo abrir la fuente: {src}")
            return

    while True:
        if is_image:
            frame = still.copy()
        else:
            ok, frame = cap.read()
            if not ok:                      # video terminado -> reiniciar
                if isinstance(src, str):
                    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    continue
                break

        # Reescalar para que el mosaico horizontal quepa en pantalla.
        scale = args.width / frame.shape[1]
        frame = cv2.resize(frame, (args.width, int(frame.shape[0] * scale)))

        blur_k = cv2.getTrackbarPos("Blur", CTRL)
        th1 = cv2.getTrackbarPos("Th1", CTRL)
        th2 = cv2.getTrackbarPos("Th2", CTRL)

        _, blurred, edges = process(frame, blur_k, th1, th2)
        view = make_view(frame, blurred, edges, show_sobel)
        cv2.imshow(WIN, view)

        key = cv2.waitKey(0 if is_image and False else 30) & 0xFF
        if key in (ord('q'), 27):
            break
        elif key == ord('g'):
            show_sobel = not show_sobel
        elif key == ord('s'):
            cv2.imwrite("canny_demo_out.jpg", view)
            print("  guardado: canny_demo_out.jpg")

    if cap is not None:
        cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
