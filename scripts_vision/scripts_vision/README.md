# scripts_vision — Complementos de visión (CapyTown)

Scripts Python de apoyo al PPTX **«Percepción Visual y Detección de Líneas Blancas»**
y a la guía de laboratorio. Permiten practicar la detección de la línea blanca
de la pista **sin necesidad del robot** y preparar los parámetros del nodo
`lane_detector` del paquete `capytown_esan_pkg`.

## Requisitos

```bash
pip install opencv-python numpy
# echo_lane_error.py además necesita ROS2 (rclpy, std_msgs)
```

## Scripts

| Script | Para qué sirve |
|--------|----------------|
| `make_chessboard_pdf.py` | Genera el patrón de ajedrez A4 imprimible (`chessboard_a4.pdf`) a tamaño real. |
| `calibrate_camera.py` | Calibra la cámara monocular con el tablero (intrínsecos K + distorsión) y guarda `camera_params.yaml`. |
| `canny_edges_demo.py` | Demo interactiva de detección de bordes (Gauss → Canny/Sobel) con umbrales en vivo. |
| `record_video.py` | Graba video de la cámara a `.mp4` (codec mp4v). Manual o por duración fija. |
| `make_test_track.py` | Genera una pista sintética (`pista_test.jpg` / `.mp4`) para probar sin robot. |
| `hsv_tuner.py` | Calibra interactivamente los 6 umbrales HSV (blanco y amarillo) y guarda `hsv_params.yaml`. |
| `ipm_picker.py` | Haces clic en 4 puntos del piso y te imprime el trapecio para `build_ipm()`. |
| `line_detect_standalone.py` | Pipeline completo (IPM→HSV→máscara→centroide→error) sin ROS, con ventana de debug. |
| `echo_lane_error.py` | Nodo ROS2 que verifica que `/lane_error` se publica correctamente. |

## Flujo de calibración de cámara (slide 6 del PPTX)

```bash
# 1. Generar e IMPRIMIR el patrón al 100 % (verifica la barra de 100 mm con regla)
python3 make_chessboard_pdf.py                     # -> chessboard_a4.pdf

# 2. Calibrar: capturar ~10-15 vistas del tablero desde varios ángulos
python3 calibrate_camera.py --source 0             # ESPACIO=capturar, c=calibrar
#   (o desde fotos)  python3 calibrate_camera.py --source "calib/*.jpg"
# Si el cuadro impreso no mide 25 mm exactos, pásalo:  --square 24.7

# Salida: camera_params.yaml con K (fx,fy,cx,cy) y distorsión (k1,k2,p1,p2,k3)
```

## Flujo sugerido (sin robot)

```bash
# 1. Crear una pista de prueba
python3 make_test_track.py --video 150        # pista_test.mp4

# 2. Calibrar los colores
python3 hsv_tuner.py --source pista_test.mp4  # tecla 's' guarda hsv_params.yaml

# 3. Ver la detección y el error lateral en vivo
python3 line_detect_standalone.py --source pista_test.mp4 --params hsv_params.yaml
```

## Flujo en el robot (con ROS2)

```bash
# Ajustar el trapecio de la IPM con una foto real de la pista
python3 ipm_picker.py --source pista_real.jpg     # pega el resultado en lane_detector.py

# Lanzar el sistema y verificar la publicación
ros2 launch capytown_esan_pkg lane_following.launch.py
python3 echo_lane_error.py                         # debe imprimir el error en metros
```

## Relación con el paquete

Estos scripts son **espejos didácticos** de la lógica de
`capytown_esan_pkg/capytown_esan/lane_detector.py`: misma segmentación HSV,
misma IPM y mismo cálculo de error lateral. La diferencia es que aquí todo corre
en un solo archivo, sin ROS, para experimentar rápido.
