#!/usr/bin/env python3
"""
turtlesim_shapes.py
-------------------
Versatile shape drawing tool for ROS 2 Turtlesim.
Supports generating custom geometric trajectories including:
  - Star (5-pointed star)
  - Circle (smooth differential arc)
  - Square
  - Equilateral Triangle
  - Hexagon / Custom Polygon
  - Archimedean Spiral
  - Simultaneous Multi-Turtle Shapes (Turtle 1 = Star, Turtle 2 = Circle, Turtle 3 = Square)

Usage:
  python3 turtlesim_shapes.py --shape star
  python3 turtlesim_shapes.py --shape circle --turtle turtle1 --speed 2.0
  python3 turtlesim_shapes.py --shape square --turtle turtle2 --size 3.0
  python3 turtlesim_shapes.py --shape triangle --turtle turtle3
  python3 turtlesim_shapes.py --shape spiral --turtle turtle1
  python3 turtlesim_shapes.py --shape simultaneous
"""

import sys
import time
import math
import argparse
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from turtlesim.srv import Spawn, SetPen, TeleportAbsolute


class TurtleShapeController(Node):
    def __init__(self, target_turtle='turtle1'):
        super().__init__('turtle_shape_controller')
        self.target_turtle = target_turtle
        self.publisher = self.create_publisher(Twist, f'/{self.target_turtle}/cmd_vel', 10)

        # Multi-turtle publishers for simultaneous mode
        self.pub_t1 = self.create_publisher(Twist, '/turtle1/cmd_vel', 10)
        self.pub_t2 = self.create_publisher(Twist, '/turtle2/cmd_vel', 10)
        self.pub_t3 = self.create_publisher(Twist, '/turtle3/cmd_vel', 10)

    def publish_twist(self, linear_x=0.0, angular_z=0.0, duration=1.0, rate_hz=20, publisher=None):
        """Publishes constant twist for a set duration at fixed frequency."""
        pub = publisher if publisher else self.publisher
        twist = Twist()
        twist.linear.x = float(linear_x)
        twist.angular.z = float(angular_z)

        steps = int(duration * rate_hz)
        dt = 1.0 / rate_hz

        for _ in range(steps):
            pub.publish(twist)
            time.sleep(dt)

        # Stop pulse
        pub.publish(Twist())
        time.sleep(0.1)

    def set_pen_color(self, turtle_name, r, g, b, width=3):
        """Configures turtle pen color and stroke width."""
        cli = self.create_client(SetPen, f'/{turtle_name}/set_pen')
        if cli.wait_for_service(timeout_sec=1.5):
            req = SetPen.Request()
            req.r, req.g, req.b, req.width, req.off = r, g, b, width, 0
            cli.call_async(req)

    def draw_star(self, side_length=2.5, speed=2.0, turtle=None):
        """
        Draws a 5-pointed star.
        Geometry: Outer tip turn angle = 180 - 36 = 144 degrees (2.5133 radians).
        """
        self.get_logger().info(f"Drawing 5-Pointed Star (Side: {side_length}m, Speed: {speed}m/s)...")
        pub = self.create_publisher(Twist, f'/{turtle}/cmd_vel', 10) if turtle else self.publisher
        self.set_pen_color(turtle or self.target_turtle, 255, 215, 0, width=3)  # Gold

        turn_angle_rad = 144.0 * (math.pi / 180.0)  # ~2.5133 rad
        turn_rate = 1.5708  # rad/s (90 deg/s)
        turn_duration = turn_angle_rad / turn_rate
        forward_duration = side_length / speed

        for point in range(1, 6):
            self.get_logger().info(f"Star: Segment {point}/5...")
            # Drive straight
            self.publish_twist(linear_x=speed, angular_z=0.0, duration=forward_duration, publisher=pub)
            # Turn 144 degrees right
            self.publish_twist(linear_x=0.0, angular_z=-turn_rate, duration=turn_duration, publisher=pub)
            time.sleep(0.2)

        self.get_logger().info("5-Pointed Star Completed!")

    def draw_circle(self, radius=1.5, speed=2.0, duration=None, turtle=None):
        """
        Draws a smooth circular path.
        Angular speed w = linear_speed / radius.
        Full circumference time = 2 * pi * radius / speed.
        """
        angular_speed = speed / radius
        if duration is None:
            duration = (2.0 * math.pi * radius) / speed

        self.get_logger().info(f"Drawing Circle (Radius: {radius}m, Speed: {speed}m/s, Duration: {duration:.2f}s)...")
        pub = self.create_publisher(Twist, f'/{turtle}/cmd_vel', 10) if turtle else self.publisher
        self.set_pen_color(turtle or self.target_turtle, 0, 200, 255, width=3)  # Cyan

        self.publish_twist(linear_x=speed, angular_z=angular_speed, duration=duration, publisher=pub)
        self.get_logger().info("Circle Completed!")

    def draw_square(self, side_length=2.5, speed=2.0, turtle=None):
        """
        Draws an exact 4-sided square.
        Turn angle = 90 degrees (1.5708 radians).
        """
        self.get_logger().info(f"Drawing Square (Side: {side_length}m, Speed: {speed}m/s)...")
        pub = self.create_publisher(Twist, f'/{turtle}/cmd_vel', 10) if turtle else self.publisher
        self.set_pen_color(turtle or self.target_turtle, 50, 255, 50, width=3)  # Green

        turn_rate = 1.5708  # 90 deg/s
        turn_duration = 1.0  # 1.5708 / 1.5708 = 1.0 s
        forward_duration = side_length / speed

        for side in range(1, 5):
            self.get_logger().info(f"Square: Side {side}/4...")
            self.publish_twist(linear_x=speed, angular_z=0.0, duration=forward_duration, publisher=pub)
            self.publish_twist(linear_x=0.0, angular_z=turn_rate, duration=turn_duration, publisher=pub)
            time.sleep(0.2)

        self.get_logger().info("Square Completed!")

    def draw_triangle(self, side_length=3.0, speed=2.0, turtle=None):
        """
        Draws an equilateral triangle.
        Turn angle = 120 degrees (2.0944 radians).
        """
        self.get_logger().info(f"Drawing Equilateral Triangle (Side: {side_length}m)...")
        pub = self.create_publisher(Twist, f'/{turtle}/cmd_vel', 10) if turtle else self.publisher
        self.set_pen_color(turtle or self.target_turtle, 255, 100, 180, width=3)  # Pink

        turn_angle_rad = 120.0 * (math.pi / 180.0)  # 2.0944 rad
        turn_rate = 1.5708
        turn_duration = turn_angle_rad / turn_rate
        forward_duration = side_length / speed

        for side in range(1, 4):
            self.get_logger().info(f"Triangle: Side {side}/3...")
            self.publish_twist(linear_x=speed, angular_z=0.0, duration=forward_duration, publisher=pub)
            self.publish_twist(linear_x=0.0, angular_z=turn_rate, duration=turn_duration, publisher=pub)
            time.sleep(0.2)

        self.get_logger().info("Triangle Completed!")

    def draw_spiral(self, speed=0.5, speed_step=0.15, angular_speed=1.5, steps=30, turtle=None):
        """
        Draws an expanding Archimedean spiral by increasing linear velocity at constant turn rate.
        """
        self.get_logger().info("Drawing Archimedean Spiral...")
        pub = self.create_publisher(Twist, f'/{turtle}/cmd_vel', 10) if turtle else self.publisher
        self.set_pen_color(turtle or self.target_turtle, 255, 140, 0, width=2)  # Orange

        cur_speed = speed
        for step in range(steps):
            self.publish_twist(linear_x=cur_speed, angular_z=angular_speed, duration=0.3, publisher=pub)
            cur_speed += speed_step

        self.get_logger().info("Spiral Completed!")

    def draw_simultaneous_shapes(self):
        """
        All three turtles draw distinct shapes concurrently:
          - Turtle 1: Star (Gold)
          - Turtle 2: Circle (Cyan)
          - Turtle 3: Square (Green)
        """
        self.get_logger().info("Executing Multi-Turtle Simultaneous Shape Drawing!")
        self.set_pen_color('turtle1', 255, 215, 0, width=3)
        self.set_pen_color('turtle2', 0, 220, 255, width=3)
        self.set_pen_color('turtle3', 50, 255, 50, width=3)

        # Run continuous synchronized publisher loop
        rate_hz = 20
        total_seconds = 8.0
        dt = 1.0 / rate_hz
        steps = int(total_seconds * rate_hz)

        t1_twist = Twist()
        t2_twist = Twist()
        t3_twist = Twist()

        t2_twist.linear.x = 2.0
        t2_twist.angular.z = 1.0  # Smooth continuous circle

        for i in range(steps):
            t = i * dt

            # Turtle 1: Star-step alternating velocity
            cycle_t = t % 1.5
            if cycle_t < 1.0:
                t1_twist.linear.x = 2.2
                t1_twist.angular.z = 0.0
            else:
                t1_twist.linear.x = 0.0
                t1_twist.angular.z = 2.5133 / 0.5  # 144 deg in 0.5s

            # Turtle 3: Square-step alternating velocity
            sq_t = t % 2.0
            if sq_t < 1.4:
                t3_twist.linear.x = 2.0
                t3_twist.angular.z = 0.0
            else:
                t3_twist.linear.x = 0.0
                t3_twist.angular.z = 1.5708 / 0.6  # 90 deg in 0.6s

            self.pub_t1.publish(t1_twist)
            self.pub_t2.publish(t2_twist)
            self.pub_t3.publish(t3_twist)
            time.sleep(dt)

        # Stop all
        stop = Twist()
        for _ in range(5):
            self.pub_t1.publish(stop)
            self.pub_t2.publish(stop)
            self.pub_t3.publish(stop)
            time.sleep(0.02)

        self.get_logger().info("Simultaneous Multi-Shape Drawing Completed!")


def main(args=None):
    parser = argparse.ArgumentParser(description="Turtlesim Custom Shape Drawing Controller")
    parser.add_argument('--turtle', default='turtle1', help="Target turtle name (turtle1, turtle2, turtle3)")
    parser.add_argument('--shape', default='star', choices=['star', 'circle', 'square', 'triangle', 'spiral', 'simultaneous'],
                        help="Shape to draw")
    parser.add_argument('--speed', type=float, default=2.0, help="Linear travel speed (m/s)")
    parser.add_argument('--size', type=float, default=2.5, help="Side length or radius scale")
    cli_args, unknown = parser.parse_known_args()

    rclpy.init(args=args)
    controller = TurtleShapeController(target_turtle=cli_args.turtle)

    try:
        if cli_args.shape == 'star':
            controller.draw_star(side_length=cli_args.size, speed=cli_args.speed)
        elif cli_args.shape == 'circle':
            controller.draw_circle(radius=cli_args.size, speed=cli_args.speed)
        elif cli_args.shape == 'square':
            controller.draw_square(side_length=cli_args.size, speed=cli_args.speed)
        elif cli_args.shape == 'triangle':
            controller.draw_triangle(side_length=cli_args.size, speed=cli_args.speed)
        elif cli_args.shape == 'spiral':
            controller.draw_spiral()
        elif cli_args.shape == 'simultaneous':
            controller.draw_simultaneous_shapes()
    except KeyboardInterrupt:
        print("\nDrawing interrupted.")
    finally:
        controller.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
