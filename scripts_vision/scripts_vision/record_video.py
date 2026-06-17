#!/usr/bin/env python3
"""record_video.py — Grabacion simple de video en .mp4 (CapyTown).

Utilidad para capturar clips de la camara y guardarlos en formato MP4. Sirve
para grabar la pista, las vistas del tablero de calibracion o material para los
otros scripts de scripts_vision (hsv_tuner, line_detect_standalone, etc.).

Solo graba: abre la camara, escribe un .mp4 y muestra una vista previa con el
tiempo y el conteo de frames. Nada de procesamiento de imagen.

Uso:
    # Grabar de la camara 0 a salida.mp4 (ENTER/ESPACIO inicia y detiene)
    python3 record_video.py

    # Elegir camara, archivo, fps y resolucion
    python3 record_video.py --source 0 --out pista.mp4 --fps 30 --size 1280x720

    # Grabar automaticamente N segundos y salir
    python3 record_video.py --out clip.mp4 --duration 15

Controles (ventana de previsualizacion):
    - ESPACIO / ENTER : inicia o pausa la grabacion (REC).
    - 'q' / ESC       : detiene y guarda el archivo.

Requiere opencv-python. El codec por defecto es mp4v (compatible con .mp4).
"""
import argparse
import time
import cv2


def parse_size(text):
    """'1280x720' -> (1280, 720). None si no se especifica."""
    if not text:
        return None
    w, h = text.lower().split("x")
    return int(w), int(h)


def main():
    ap = argparse.ArgumentParser(description="Grabador de video .mp4 (CapyTown).")
    ap.add_argument("--source", default="0",
                    help="indice de camara (0 por defecto).")
    ap.add_argument("--out", default="salida.mp4",
                    help="archivo de salida .mp4.")
    ap.add_argument("--fps", type=float, default=30.0,
                    help="cuadros por segundo del archivo (def. 30).")
    ap.add_argument("--size", default=None,
                    help="resolucion deseada, ej. 1280x720 (def. la de la camara).")
    ap.add_argument("--duration", type=float, default=0.0,
                    help="segundos a grabar automaticamente; 0 = manual.")
    args = ap.parse_args()

    src = int(args.source) if args.source.isdigit() else args.source
    cap = cv2.VideoCapture(src)
    if not cap.isOpened():
        print(f"No se pudo abrir la camara/fuente: {src}")
        return

    # Pedir resolucion a la camara si el usuario la indico.
    want = parse_size(args.size)
    if want:
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, want[0])
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, want[1])

    # Resolucion real (puede diferir de la pedida).
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")     # codec para .mp4
    writer = cv2.VideoWriter(args.out, fourcc, args.fps, (w, h))
    if not writer.isOpened():
        print("No se pudo crear el VideoWriter (revisa codec/permisos).")
        cap.release()
        return

    auto = args.duration > 0
    recording = auto                              # en modo --duration arranca grabando
    frames = 0
    t_start = None
    print(f"Salida: {args.out}  ({w}x{h} @ {args.fps:g} fps)")
    if auto:
        print(f"Grabando {args.duration:g} s automaticamente...")
        t_start = time.time()
    else:
        print("ESPACIO/ENTER = REC/pausa · q/ESC = detener y guardar")

    while True:
        ok, frame = cap.read()
        if not ok:
            print("Fin de la fuente o error de lectura.")
            break

        if recording:
            writer.write(frame)
            frames += 1

        # --- Overlay de estado ---
        prev = frame.copy()
        if recording:
            cv2.circle(prev, (24, 24), 9, (0, 0, 255), -1)   # punto rojo REC
            elapsed = (time.time() - t_start) if t_start else frames / args.fps
            cv2.putText(prev, f"REC  {elapsed:5.1f}s  ({frames} frames)",
                        (40, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6,
                        (0, 0, 255), 2, cv2.LINE_AA)
        else:
            cv2.putText(prev, "PAUSA — ESPACIO para grabar",
                        (40, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6,
                        (0, 255, 255), 2, cv2.LINE_AA)
        cv2.imshow("Grabador .mp4 — CapyTown", prev)

        # Parada automatica por duracion.
        if auto and (time.time() - t_start) >= args.duration:
            break

        key = cv2.waitKey(1) & 0xFF
        if key in (ord('q'), 27):
            break
        elif key in (ord(' '), 13) and not auto:
            recording = not recording
            if recording and t_start is None:
                t_start = time.time()

    writer.release()
    cap.release()
    cv2.destroyAllWindows()
    secs = frames / args.fps if args.fps else 0
    print(f"Guardado: {args.out}  ·  {frames} frames  ·  ~{secs:.1f} s")


if __name__ == "__main__":
    main()
