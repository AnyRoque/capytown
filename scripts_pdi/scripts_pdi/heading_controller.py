#!/usr/bin/env python3
"""CapyTown heading_controller — Semana 11 (RC-2), Experimento 1 "Camina recto, chaski".

El lazo PID mas simple posible (diapositiva 7 de la clase):

    Setpoint : el yaw inicial  theta0  al arrancar el nodo.
    Error    : e = normalize(theta0 - yaw(t))   en rad, en [-pi, pi].
    Accion   : w = PID(e),  con velocidad lineal fija v = 0.20 m/s.

Por que empezar aqui (y no con la camara):
  - Un solo topico de entrada (/odom) y cero calibracion de camara.
  - Lo que ves en la grafica es el controlador puro, sin ruido del pipeline de vision.
  - El MISMO esqueleto PID se reutiliza luego en lane_controller.py con /lane_error.

Version de referencia (TODO resueltos). Para la version del alumno,
reemplazar el bloque marcado por '# --- PID (TODO alumno) ---'.

Uso (en el Pi5 / VM con ROS2 Humble):
  ros2 run capytown_esan heading_controller
  # o sin instalar el paquete:
  python3 heading_controller.py
  # cambiar ganancias en caliente (una a la vez, regla TPACK):
  python3 heading_controller.py --ros-args -p kp:=2.5 -p kd:=0.3
"""
import math

import rclpy
from rclpy.node import Node
from nav_msgs.msg import Odometry
from geometry_msgs.msg import Twist


def normalize(a: float) -> float:
    """Normaliza un angulo a [-pi, pi] (mismo helper que core_pid.py)."""
    return (a + math.pi) % (2.0 * math.pi) - math.pi


def yaw_from_quat(q) -> float:
    """Extrae el yaw (rotacion en Z) de un quaternion geometry_msgs/Quaternion."""
    siny_cosp = 2.0 * (q.w * q.z + q.x * q.y)
    cosy_cosp = 1.0 - 2.0 * (q.y * q.y + q.z * q.z)
    return math.atan2(siny_cosp, cosy_cosp)


class HeadingController(Node):
    def __init__(self):
        super().__init__('heading_controller')
        self.declare_parameters('', [
            ('kp', 2.5), ('ki', 0.0), ('kd', 0.3),
            ('linear_speed', 0.20),
            ('max_angular', 2.0),
            ('integral_limit', 0.5),
            ('odom_timeout', 0.5),
            ('control_rate', 30.0),
        ])
        gp = self.get_parameter
        self.kp = gp('kp').value
        self.ki = gp('ki').value
        self.kd = gp('kd').value
        self.v = gp('linear_speed').value
        self.max_w = gp('max_angular').value
        self.i_limit = gp('integral_limit').value
        self.timeout = gp('odom_timeout').value
        rate = gp('control_rate').value

        # Estado del controlador
        self.yaw0 = None          # setpoint: yaw al arrancar (lo fija el 1er /odom)
        self.yaw = None           # yaw actual
        self.i_acc = 0.0          # acumulador del termino integral
        self.e_prev = 0.0         # error anterior (para el termino derivativo)
        self.last_stamp = self.get_clock().now()
        self.last_rx = self.get_clock().now()

        self.sub = self.create_subscription(Odometry, '/odom', self.on_odom, 10)
        self.pub = self.create_publisher(Twist, '/cmd_vel', 10)
        self.timer = self.create_timer(1.0 / rate, self.control_loop)
        self.get_logger().info('heading_controller listo. Esperando /odom...')

    def on_odom(self, msg):
        self.yaw = yaw_from_quat(msg.pose.pose.orientation)
        self.last_rx = self.get_clock().now()
        if self.yaw0 is None:                       # fija el rumbo objetivo una sola vez
            self.yaw0 = self.yaw
            self.get_logger().info(
                f'Rumbo objetivo theta0 = {math.degrees(self.yaw0):.1f} deg')

    def control_loop(self):
        now = self.get_clock().now()
        dt = (now - self.last_stamp).nanoseconds * 1e-9
        self.last_stamp = now
        if dt <= 0.0:
            return

        # Seguridad: sin odometria reciente (o aun sin setpoint) => frenar
        age = (now - self.last_rx).nanoseconds * 1e-9
        if self.yaw0 is None or self.yaw is None or age > self.timeout:
            self.pub.publish(Twist())   # v=0, w=0
            self.i_acc = 0.0
            return

        e = normalize(self.yaw0 - self.yaw)         # error angular en [-pi, pi]

        # --- PID (TODO alumno) ---
        p = self.kp * e
        self.i_acc += e * dt
        self.i_acc = max(-self.i_limit, min(self.i_limit, self.i_acc))   # anti-windup
        d = (e - self.e_prev) / dt
        w = p + self.ki * self.i_acc + self.kd * d
        self.e_prev = e
        # --- fin PID ---

        cmd = Twist()
        cmd.linear.x = self.v
        cmd.angular.z = max(-self.max_w, min(self.max_w, w))   # saturacion
        self.pub.publish(cmd)


def main(args=None):
    rclpy.init(args=args)
    node = HeadingController()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.pub.publish(Twist())       # frena al salir
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
