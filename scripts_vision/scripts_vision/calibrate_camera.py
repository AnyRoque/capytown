#!/usr/bin/env python3
"""calibrate_camera.py — Calibracion de camara monocular con tablero de ajedrez (CapyTown).

Complemento del PPTX «Percepcion Visual y Deteccion de Lineas Blancas», Bloque 2,
slide «Calibracion de la camara». Reproduce de forma didactica lo que el curso
Yahboom 08 · 1 «Monocular camera calibration» hace: detecta las esquinas de un
tablero de ajedrez en varias vistas y llama a cv2.calibrateCamera para obtener:

    - la matriz intrinseca K  (fx, fy, cx, cy)  -> la geometria interna del lente
    - los coeficientes de distorsion (k1, k2, p1, p2, k3) -> el efecto barril

Como dice la slide 6: SIN calibrar, la posicion de la linea sale con error y el
robot se desvia sistematicamente. La calibracion + la homografia (IPM) son lo
que permite medir distancias reales (metros) a partir de pixeles.

Imprime primero el patron `chessboard_a4.pdf` (mismo folder) a tamano REAL (sin
«ajustar a pagina») y pegalo sobre una superficie rigida y plana.

Uso:
    # Capturar en vivo desde la camara y calibrar (recomendado)
    python3 calibrate_camera.py --source 0

    # Calibrar a partir de fotos ya tomadas del tablero
    python3 calibrate_camera.py --source "calib_imgs/*.jpg"

    # Ajustar la geometria del tablero (esquinas INTERNAS) y el lado del cuadro
    python3 calibrate_camera.py --source 0 --cols 9 --rows 6 --square 25

Parametros del tablero (deben coincidir con el PDF impreso):
    --cols / --rows : numero de esquinas INTERNAS (no de cuadros).
                      El patron por defecto (10x7 cuadros) tiene 9x6 esquinas.
    --square        : lado de cada cuadro en milimetros (mide con regla el
                      impreso real; el escalado de la impresora puede variar).

Controles en modo camara:
    - ESPACIO : captura la vista actual si detecta el tablero (verde = OK).
    - 'c'     : calibra con las vistas capturadas (necesita >= --min vistas).
    - 'u'     : alterna vista normal / sin distorsion (undistort) tras calibrar.
    - 'q'/ESC : salir.

Salida: `camera_params.yaml` con K, dist, resolucion y error de reproyeccion.
Formato compatible con un nodo de calibracion del paquete capytown_esan_pkg.
"""
import argparse
import glob
import os
import cv2
import numpy as np

WIN = "Calibracion de camara — CapyTown"


def build_object_points(cols, rows, square_mm):
    """Coordenadas 3D del tablero (Z=0), en metros. (rows*cols, 3)."""
    objp = np.zeros((rows * cols, 3), np.float32)
    objp[:, :2] = np.mgrid[0:cols, 0:rows].T.reshape(-1, 2)
    objp *= (square_mm / 1000.0)  # mm -> m
    return objp


# Criterio de parada para el refinamiento sub-pixel de las esquinas.
SUBPIX = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)


def find_corners(gray, pattern):
    """Busca el tablero y refina a sub-pixel. Devuelve (ok, corners)."""
    flags = cv2.CALIB_CB_ADAPTIVE_THRESH | cv2.CALIB_CB_NORMALIZE_IMAGE
    ok, corners = cv2.findChessboardCorners(gray, pattern, flags)
    if ok:
        corners = cv2.cornerSubPix(gray, corners, (11, 11), (-1, -1), SUBPIX)
    return ok, corners


def calibrate(objpoints, imgpoints, image_size):
    """Llama a cv2.calibrateCamera y calcula el error medio de reproyeccion."""
    ret, K, dist, rvecs, tvecs = cv2.calibrateCamera(
        objpoints, imgpoints, image_size, None, None
    )
    # Error de reproyeccion: cuanto se aleja (en pixeles) la esquina reproyectada
    # de la detectada. < 0.5 px es bueno; > 1 px conviene recapturar.
    total = 0.0
    for i in range(len(objpoints)):
        proj, _ = cv2.projectPoints(objpoints[i], rvecs[i], tvecs[i], K, dist)
        total += cv2.norm(imgpoints[i], proj, cv2.NORM_L2) / len(proj)
    rms = total / len(objpoints)
    return K, dist, rms


def save_yaml(path, K, dist, image_size, rms, pattern, square_mm, n_views):
    fx, fy = K[0, 0], K[1, 1]
    cx, cy = K[0, 2], K[1, 2]
    d = dist.ravel().tolist()
    d += [0.0] * (5 - len(d))
    w, h = image_size
    with open(path, "w") as f:
        f.write("# camera_params.yaml — Calibracion monocular (CapyTown)\n")
        f.write("# Generado por calibrate_camera.py · curso Yahboom 08-1\n")
        f.write("# K = [[fx,0,cx],[0,fy,cy],[0,0,1]] · dist = [k1,k2,p1,p2,k3]\n")
        f.write("camera_matrix:\n")
        f.write("  rows: 3\n  cols: 3\n")
        f.write(f"  data: [{K[0,0]:.6f}, 0.0, {cx:.6f},\n")
        f.write(f"         0.0, {K[1,1]:.6f}, {cy:.6f},\n")
        f.write("         0.0, 0.0, 1.0]\n")
        f.write(f"fx: {fx:.6f}\nfy: {fy:.6f}\ncx: {cx:.6f}\ncy: {cy:.6f}\n")
        f.write("distortion_coefficients:\n")
        f.write("  rows: 1\n  cols: 5\n")
        f.write(f"  data: [{d[0]:.6f}, {d[1]:.6f}, {d[2]:.6f}, {d[3]:.6f}, {d[4]:.6f}]\n")
        f.write(f"image_width: {w}\nimage_height: {h}\n")
        f.write(f"reprojection_error_px: {rms:.4f}\n")
        f.write(f"board_inner_corners: [{pattern[0]}, {pattern[1]}]\n")
        f.write(f"square_size_m: {square_mm/1000.0:.4f}\n")
        f.write(f"num_views: {n_views}\n")


def report(K, dist, rms, n):
    print("\n" + "=" * 52)
    print(f"  Calibracion lista con {n} vistas")
    print("=" * 52)
    print(f"  fx = {K[0,0]:8.2f} px     fy = {K[1,1]:8.2f} px")
    print(f"  cx = {K[0,2]:8.2f} px     cy = {K[1,2]:8.2f} px")
    print(f"  dist (k1,k2,p1,p2,k3) = {np.round(dist.ravel(), 5).tolist()}")
    print(f"  Error de reproyeccion = {rms:.4f} px", end="")
    print("   (OK)" if rms < 0.6 else "   (alto: recaptura vistas)")
    print("=" * 52 + "\n")


def run_from_images(paths, pattern, square_mm, out):
    objp = build_object_points(pattern[0], pattern[1], square_mm)
    objpoints, imgpoints = [], []
    image_size = None
    used = 0
    for p in paths:
        img = cv2.imread(p)
        if img is None:
            print(f"  [skip] no se pudo leer {p}")
            continue
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        image_size = gray.shape[::-1]
        ok, corners = find_corners(gray, pattern)
        print(f"  {'[OK]  ' if ok else '[----]'} {os.path.basename(p)}")
        if ok:
            objpoints.append(objp)
            imgpoints.append(corners)
            used += 1
    if used < 3:
        print(f"\nSolo {used} vistas validas. Se necesitan al menos 3 (idealmente 10-15).")
        return
    K, dist, rms = calibrate(objpoints, imgpoints, image_size)
    report(K, dist, rms, used)
    save_yaml(out, K, dist, image_size, rms, pattern, square_mm, used)
    print(f"Guardado: {out}")


def run_from_camera(index, pattern, square_mm, out, min_views):
    objp = build_object_points(pattern[0], pattern[1], square_mm)
    objpoints, imgpoints = [], []
    image_size = None
    K = dist = None
    show_undistort = False

    cap = cv2.VideoCapture(index)
    if not cap.isOpened():
        print(f"No se pudo abrir la camara {index}.")
        return
    print(__doc__.split("Uso:")[0])
    print("ESPACIO=capturar  c=calibrar  u=undistort  q=salir\n")

    while True:
        ok_frame, frame = cap.read()
        if not ok_frame:
            break
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        image_size = gray.shape[::-1]
        found, corners = find_corners(gray, pattern)

        if show_undistort and K is not None:
            view = cv2.undistort(frame, K, dist)
            tag = "SIN DISTORSION (undistort)"
        else:
            view = frame.copy()
            if found:
                cv2.drawChessboardCorners(view, pattern, corners, found)
            tag = "tablero DETECTADO" if found else "buscando tablero..."

        color = (0, 220, 0) if found else (0, 165, 255)
        cv2.putText(view, tag, (12, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
        cv2.putText(view, f"vistas capturadas: {len(objpoints)}/{min_views}",
                    (12, 56), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        cv2.imshow(WIN, view)

        key = cv2.waitKey(1) & 0xFF
        if key in (ord('q'), 27):
            break
        elif key == ord(' ') and found:
            objpoints.append(objp)
            imgpoints.append(corners)
            print(f"  + vista {len(objpoints)} capturada")
        elif key == ord('c'):
            if len(objpoints) < min_views:
                print(f"  Faltan vistas: {len(objpoints)}/{min_views}")
                continue
            K, dist, rms = calibrate(objpoints, imgpoints, image_size)
            report(K, dist, rms, len(objpoints))
            save_yaml(out, K, dist, image_size, rms, pattern, square_mm, len(objpoints))
            print(f"Guardado: {out}  (pulsa 'u' para ver el undistort)")
        elif key == ord('u'):
            show_undistort = not show_undistort

    cap.release()
    cv2.destroyAllWindows()


def main():
    ap = argparse.ArgumentParser(
        description="Calibracion monocular con tablero de ajedrez (CapyTown).")
    ap.add_argument("--source", default="0",
                    help="indice de camara (0), o patron glob de imagenes "
                         "(ej. 'calib/*.jpg').")
    ap.add_argument("--cols", type=int, default=9,
                    help="esquinas INTERNAS en horizontal (def. 9).")
    ap.add_argument("--rows", type=int, default=6,
                    help="esquinas INTERNAS en vertical (def. 6).")
    ap.add_argument("--square", type=float, default=25.0,
                    help="lado del cuadro en mm del impreso real (def. 25).")
    ap.add_argument("--out", default="camera_params.yaml",
                    help="archivo YAML de salida.")
    ap.add_argument("--min", type=int, default=10,
                    help="vistas minimas para calibrar en modo camara (def. 10).")
    args = ap.parse_args()

    pattern = (args.cols, args.rows)
    print(f"Tablero: {pattern[0]}x{pattern[1]} esquinas internas · "
          f"cuadro {args.square} mm")

    # ¿La fuente es una camara (entero) o un glob de imagenes?
    if args.source.isdigit():
        run_from_camera(int(args.source), pattern, args.square, args.out, args.min)
    else:
        paths = sorted(glob.glob(args.source))
        if not paths:
            print(f"No se encontraron imagenes para: {args.source}")
            return
        run_from_images(paths, pattern, args.square, args.out)


if __name__ == "__main__":
    main()
