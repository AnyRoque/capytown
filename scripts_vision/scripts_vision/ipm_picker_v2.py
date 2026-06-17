#!/usr/bin/env python3
"""ipm_picker_v2.py — Selector de los 4 puntos del trapecio IPM (CapyTown).

Version mejorada de ipm_picker.py. Ademas de elegir los 4 puntos del piso para
la Inverse Perspective Mapping, esta version:
  * GUARDA el resultado en ipm_config.json (pixeles + normalizado) -> no se pierde.
  * REANUDA desde un ipm_config.json existente.
  * Permite ARRASTRAR un punto ya puesto para ajustarlo fino.
  * DESHACER el ultimo punto (tecla 'u').
  * CONGELAR el cuadro de la camara (barra espaciadora) para clicar sobre una
    imagen quieta.
  * PREVISUALIZA la vista de pajaro en vivo y dibuja la region destino.
  * VALIDA que el cuadrilatero no sea degenerado.
  * GUARDA una imagen del warp (tecla 'g') para el informe.
  * Imprime el snippet listo para pegar en build_ipm() de lane_detector.py.

Uso:
    python3 ipm_picker_v2.py --source pista.jpg
    python3 ipm_picker_v2.py --source 0 --out ipm_config.json

Orden de clics:  1) Sup-Izq   2) Sup-Der   3) Inf-Der   4) Inf-Izq
Teclas: [espacio] congela/descongela camara | [u] deshacer | [r] reiniciar
        [p] preview vista pajaro | [g] guardar warp | [s] guardar json | [q] salir
"""
import argparse
import json
import os
import cv2
import numpy as np

LABELS = ["TL (sup-izq)", "TR (sup-der)", "BR (inf-der)", "BL (inf-izq)"]
COLORS = [(0, 0, 255), (0, 165, 255), (0, 255, 255), (255, 0, 0)]
HIT_RADIUS = 12          # px para "agarrar" un punto al arrastrar

# La region destino (rectangulo) en la vista de pajaro: el carril queda centrado
# ocupando de DST_MARGIN a (1 - DST_MARGIN) del ancho.
DST_MARGIN = 0.30


class PickerState:
    def __init__(self, pts=None):
        self.pts = list(pts) if pts else []   # lista de (x, y) en px de la vista
        self.dragging = None                  # indice del punto que se arrastra


def make_mouse_cb(state):
    def cb(event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN:
            # arrastrar un punto existente si el clic cae cerca
            for i, (px, py) in enumerate(state.pts):
                if (px - x) ** 2 + (py - y) ** 2 <= HIT_RADIUS ** 2:
                    state.dragging = i
                    return
            if len(state.pts) < 4:            # si no, agregar uno nuevo
                state.pts.append((x, y))
        elif event == cv2.EVENT_MOUSEMOVE and state.dragging is not None:
            state.pts[state.dragging] = (x, y)
        elif event == cv2.EVENT_LBUTTONUP:
            state.dragging = None
    return cb


def quad_is_valid(pts):
    """Area no nula y vertices distintos -> cuadrilatero usable."""
    if len(pts) != 4:
        return False
    p = np.array(pts, np.float32)
    area = 0.0
    for i in range(4):
        x1, y1 = p[i]
        x2, y2 = p[(i + 1) % 4]
        area += x1 * y2 - x2 * y1
    return abs(area) / 2.0 > 100.0            # area minima razonable (px^2)


def homography(pts, w, h):
    src = np.float32(pts)
    dst = np.float32([[DST_MARGIN * w, 0], [(1 - DST_MARGIN) * w, 0],
                      [(1 - DST_MARGIN) * w, h], [DST_MARGIN * w, h]])
    return cv2.getPerspectiveTransform(src, dst), dst


def draw_overlay(frame, state, frozen):
    h, w = frame.shape[:2]
    img = frame.copy()
    for i, (x, y) in enumerate(state.pts):
        cv2.circle(img, (x, y), 7, COLORS[i], -1)
        cv2.circle(img, (x, y), 9, (255, 255, 255), 1)
        cv2.putText(img, str(i + 1), (x + 10, y - 6),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, COLORS[i], 2)
    if len(state.pts) >= 2:
        cv2.polylines(img, [np.array(state.pts, np.int32)],
                      len(state.pts) == 4, (0, 255, 0), 2)
    # barra de estado
    nxt = LABELS[len(state.pts)] if len(state.pts) < 4 else "completo (arrastra para ajustar)"
    status = f"Puntos: {len(state.pts)}/4  ->  siguiente: {nxt}"
    if frozen:
        status += "   [CONGELADO]"
    cv2.rectangle(img, (0, 0), (w, 26), (40, 40, 40), -1)
    cv2.putText(img, status, (8, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.55,
                (255, 255, 255), 1)
    cv2.putText(img, "espacio=congela u=deshacer r=reset p=preview g=warp s=guardar q=salir",
                (8, h - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (200, 255, 200), 1)
    return img


def normalized(pts, w, h):
    return [(round(x / w, 4), round(y / h, 4)) for (x, y) in pts]


def save_json(pts, w, h, path):
    data = {
        "image_size": {"w": w, "h": h},
        "dst_margin": DST_MARGIN,
        "points_px": [list(p) for p in pts],
        "points_norm": [list(p) for p in normalized(pts, w, h)],
    }
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
    print(f"[ipm_picker_v2] Guardado en {path}")
    print_snippet(pts, w, h)


def load_json(path, w, h):
    if not (path and os.path.exists(path)):
        return None
    try:
        data = json.load(open(path))
        norm = data["points_norm"]
        return [(int(nx * w), int(ny * h)) for nx, ny in norm]
    except Exception as e:
        print(f"[ipm_picker_v2] No pude cargar {path}: {e}")
        return None


def print_snippet(pts, w, h):
    norm = normalized(pts, w, h)
    print("\n# --- Pega esto dentro de build_ipm(self, w, h) en lane_detector.py ---")
    print("        src = np.float32([")
    for (nx, ny), lab in zip(norm, LABELS):
        print(f"            [{nx:.2f} * w, {ny:.2f} * h],   # {lab}")
    print("        ])")
    print(f"        dst = np.float32([[{DST_MARGIN:.2f} * w, 0.0], "
          f"[{1 - DST_MARGIN:.2f} * w, 0.0],")
    print(f"                          [{1 - DST_MARGIN:.2f} * w, h], "
          f"[{DST_MARGIN:.2f} * w, h]])")
    print("        self.M = cv2.getPerspectiveTransform(src, dst)\n")


def open_source(source):
    """Devuelve (frame_estatico | None, cap | None)."""
    if source.isdigit():
        cap = cv2.VideoCapture(int(source))
        return None, (cap if cap.isOpened() else None)
    img = cv2.imread(source)
    if img is not None:
        return img, None
    cap = cv2.VideoCapture(source)
    return None, (cap if cap.isOpened() else None)


def main():
    ap = argparse.ArgumentParser(description="Selector de puntos IPM (CapyTown)")
    ap.add_argument("--source", default="0", help="camara (0), imagen o video")
    ap.add_argument("--width", type=int, default=640)
    ap.add_argument("--height", type=int, default=480)
    ap.add_argument("--out", default="ipm_config.json")
    args = ap.parse_args()

    static, cap = open_source(args.source)
    if static is None and cap is None:
        raise SystemExit(f"No pude abrir la fuente: {args.source}")

    w, h = args.width, args.height
    state = PickerState(load_json(args.out, w, h))
    if state.pts:
        print(f"[ipm_picker_v2] Reanudando desde {args.out} ({len(state.pts)} puntos).")

    win = "IPM Picker v2"
    cv2.namedWindow(win)
    cv2.setMouseCallback(win, make_mouse_cb(state))
    frozen = static is not None        # una imagen ya esta 'congelada'
    held = static.copy() if static is not None else None

    while True:
        if frozen and held is not None:
            frame = held.copy()
        else:
            ok, frame = cap.read() if cap else (False, None)
            if not ok:
                if cap:
                    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    continue
                break
        frame = cv2.resize(frame, (w, h))
        cv2.imshow(win, draw_overlay(frame, state, frozen))

        k = cv2.waitKey(20) & 0xFF
        if k in (ord('q'), 27):
            break
        elif k == ord(' ') and cap is not None:     # congelar/descongelar
            frozen = not frozen
            if frozen:
                held = frame.copy()
        elif k == ord('u') and state.pts:           # deshacer
            state.pts.pop()
        elif k == ord('r'):                         # reiniciar
            state.pts.clear()
        elif k in (ord('p'), ord('g')) and quad_is_valid(state.pts):
            M, dst = homography(state.pts, w, h)
            warp = cv2.warpPerspective(frame, M, (w, h))
            cv2.polylines(warp, [dst.astype(np.int32)], True, (0, 255, 0), 1)
            cv2.imshow("Vista de pajaro (preview)", warp)
            if k == ord('g'):
                cv2.imwrite("ipm_preview.jpg", warp)
                print("[ipm_picker_v2] Warp guardado en ipm_preview.jpg")
        elif k in (ord('p'), ord('g')) and not quad_is_valid(state.pts):
            print("[ipm_picker_v2] Necesitas 4 puntos validos (cuadrilatero no degenerado).")
        elif k == ord('s'):                         # guardar json + snippet
            if quad_is_valid(state.pts):
                save_json(state.pts, w, h, args.out)
            else:
                print("[ipm_picker_v2] Aun no hay 4 puntos validos para guardar.")

    if quad_is_valid(state.pts):
        save_json(state.pts, w, h, args.out)        # autosave al salir
    if cap is not None:
        cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
