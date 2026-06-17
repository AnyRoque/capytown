#!/usr/bin/env python3
"""make_chessboard_pdf.py — Genera el patron de ajedrez A4 para calibrar (CapyTown).

Crea `chessboard_a4.pdf`: un tablero de ajedrez a TAMANO FISICO EXACTO listo para
imprimir en A4. Es el patron que usa `calibrate_camera.py` (curso Yahboom 08-1).

Por defecto: 10x7 cuadros  ->  9x6 esquinas INTERNAS  ->  --cols 9 --rows 6
Lado del cuadro: 25 mm.

Reglas de impresion (¡importantes para que la calibracion sea correcta!):
    - Imprime al 100 % / «Tamano real». NUNCA «Ajustar a pagina».
    - Verifica con una regla la barra de control de 100 mm del pie.
    - Si el cuadro real no mide 25 mm, pasa el valor medido a calibrate_camera.py
      con --square (ej. --square 24.7).
    - Pega la hoja sobre una superficie rigida y plana (carton/MDF), sin arrugas.

Uso:
    python3 make_chessboard_pdf.py                       # 10x7 cuadros, 25 mm
    python3 make_chessboard_pdf.py --sq-cols 8 --sq-rows 6 --square 30
"""
import argparse
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas


def make_pdf(out, sq_cols, sq_rows, square_mm):
    page_w, page_h = landscape(A4)           # 297 x 210 mm en puntos
    s = square_mm * mm
    board_w = sq_cols * s
    board_h = sq_rows * s

    if board_w > page_w - 16 * mm or board_h > page_h - 28 * mm:
        raise SystemExit(
            f"El tablero ({sq_cols*square_mm}x{sq_rows*square_mm} mm) no cabe en A4. "
            "Reduce --square o el numero de cuadros.")

    # Centrado horizontal; dejamos un margen inferior para los rotulos.
    x0 = (page_w - board_w) / 2.0
    y0 = (page_h - board_h) / 2.0 + 6 * mm

    c = canvas.Canvas(out, pagesize=(page_w, page_h))

    # --- Cuadros negros (esquina inferior-izquierda negra) ---
    c.setFillColorRGB(0, 0, 0)
    for r in range(sq_rows):
        for col in range(sq_cols):
            if (r + col) % 2 == 0:
                c.rect(x0 + col * s, y0 + r * s, s, s, stroke=0, fill=1)

    # Borde fino alrededor del tablero (ayuda a recortar / encuadrar)
    c.setLineWidth(0.3)
    c.setStrokeColorRGB(0, 0, 0)
    c.rect(x0, y0, board_w, board_h, stroke=1, fill=0)

    inner = (sq_cols - 1, sq_rows - 1)

    # --- Rotulos superiores ---
    c.setFillColorRGB(0, 0, 0)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(x0, y0 + board_h + 9 * mm,
                 "CapyTown · Calibracion de camara monocular")
    c.setFont("Helvetica", 9)
    c.drawString(x0, y0 + board_h + 4 * mm,
                 f"Tablero {sq_cols}x{sq_rows} cuadros  ·  esquinas internas "
                 f"{inner[0]}x{inner[1]}  ·  cuadro = {square_mm:g} mm")

    # --- Pie: parametros + barra de verificacion de 100 mm ---
    c.setFont("Helvetica", 8)
    c.drawString(x0, y0 - 9 * mm,
                 f"calibrate_camera.py  --cols {inner[0]}  --rows {inner[1]}  "
                 f"--square {square_mm:g}")
    c.drawString(x0, y0 - 14 * mm,
                 "Imprimir al 100% (tamano real). NO ajustar a pagina. "
                 "Pegar sobre superficie rigida y plana.")

    # Barra de control de 100 mm para verificar la escala con una regla.
    bar_x = x0
    bar_y = y0 - 21 * mm
    c.setLineWidth(1)
    c.line(bar_x, bar_y, bar_x + 100 * mm, bar_y)
    for i in range(11):                       # ticks cada 10 mm
        tx = bar_x + i * 10 * mm
        th = 2.5 * mm if i % 5 else 4 * mm
        c.line(tx, bar_y, tx, bar_y + th)
    c.setFont("Helvetica", 7)
    c.drawString(bar_x + 100 * mm + 3 * mm, bar_y - 1 * mm,
                 "<- esta barra debe medir 100 mm con regla")

    c.showPage()
    c.save()
    print(f"Generado: {out}")
    print(f"  {sq_cols}x{sq_rows} cuadros · esquinas internas {inner[0]}x{inner[1]} "
          f"· cuadro {square_mm:g} mm · tablero {sq_cols*square_mm:g}x"
          f"{sq_rows*square_mm:g} mm")


def main():
    ap = argparse.ArgumentParser(description="Patron de ajedrez A4 (CapyTown).")
    ap.add_argument("--out", default="chessboard_a4.pdf")
    ap.add_argument("--sq-cols", type=int, default=10,
                    help="cuadros en horizontal (def. 10 -> 9 esquinas internas).")
    ap.add_argument("--sq-rows", type=int, default=7,
                    help="cuadros en vertical (def. 7 -> 6 esquinas internas).")
    ap.add_argument("--square", type=float, default=25.0,
                    help="lado del cuadro en mm (def. 25).")
    args = ap.parse_args()
    make_pdf(args.out, args.sq_cols, args.sq_rows, args.square)


if __name__ == "__main__":
    main()
