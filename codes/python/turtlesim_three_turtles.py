#!/usr/bin/env python3
"""
turtlesim_three_turtles.py
--------------------------
Simultaneous movement of three turtles in the same turtlesim environment
using separate ROS 2 namespaces (/turtle1, /turtle2, /turtle3).

Demonstrates:
  1. Spawning turtle1, turtle2, turtle3 at custom initial coordinates.
  2. Setting distinct pen colors (Red, Green, Blue) for each turtle.
  3. Teleporting and synchronizing starting orientations.
  4. Publishing velocity commands to all three namespaces concurrently
     so all three robots execute synchronized motion trajectories at the same time.
"""

import sys
import time
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from turtlesim.srv import Spawn, TeleportAbsolute, SetPen


class ThreeTurtleSimultaneous(Node):
    def __init__(self):
        super().__init__('three_turtle_simultaneous')

        # Velocity Publishers for each turtle namespace
        self.pub_t1 = self.create_publisher(Twist, '/turtle1/cmd_vel', 10)
        self.pub_t2 = self.create_publisher(Twist, '/turtle2/cmd_vel', 10)
        self.pub_t3 = self.create_publisher(Twist, '/turtle3/cmd_vel', 10)

        self.get_logger().info("Initializing Three Turtle Simultaneous Movement Node...")

    def call_service_sync(self, client, request, name):
        """Helper to wait for and call a ROS 2 service."""
        if not client.wait_for_service(timeout_sec=2.0):
            self.get_logger().warn(f"Service {name} not available, continuing...")
            return None
        future = client.call_async(request)
        rclpy.spin_until_future_complete(self, future, timeout_sec=3.0)
        return future.result()

    def setup_turtles(self):
        """Spawn turtle2 and turtle3 (turtle1 exists by default in turtlesim)."""
        spawn_cli = self.create_client(Spawn, '/spawn')

        # Spawn turtle2 at (5.0, 2.0)
        req2 = Spawn.Request()
        req2.x, req2.y, req2.theta, req2.name = 5.0, 2.0, 0.0, 'turtle2'
        self.call_service_sync(spawn_cli, req2, '/spawn (turtle2)')

        # Spawn turtle3 at (8.0, 2.0)
        req3 = Spawn.Request()
        req3.x, req3.y, req3.theta, req3.name = 8.0, 2.0, 0.0, 'turtle3'
        self.call_service_sync(spawn_cli, req3, '/spawn (turtle3)')

        # Set distinctive pen colors:
        # Turtle1 -> RED
        pen1 = self.create_client(SetPen, '/turtle1/set_pen')
        req_pen1 = SetPen.Request()
        req_pen1.r, req_pen1.g, req_pen1.b, req_pen1.width, req_pen1.off = 255, 50, 50, 3, 0
        self.call_service_sync(pen1, req_pen1, '/turtle1/set_pen')

        # Turtle2 -> GREEN
        pen2 = self.create_client(SetPen, '/turtle2/set_pen')
        req_pen2 = SetPen.Request()
        req_pen2.r, req_pen2.g, req_pen2.b, req_pen2.width, req_pen2.off = 50, 255, 50, 3, 0
        self.call_service_sync(pen2, req_pen2, '/turtle2/set_pen')

        # Turtle3 -> BLUE
        pen3 = self.create_client(SetPen, '/turtle3/set_pen')
        req_pen3 = SetPen.Request()
        req_pen3.r, req_pen3.g, req_pen3.b, req_pen3.width, req_pen3.off = 50, 100, 255, 3, 0
        self.call_service_sync(pen3, req_pen3, '/turtle3/set_pen')

        # Teleport to starting positions with heading = 90 deg (pi/2 rad = 1.5708)
        teleport1 = self.create_client(TeleportAbsolute, '/turtle1/teleport_absolute')
        t1_req = TeleportAbsolute.Request()
        t1_req.x, t1_req.y, t1_req.theta = 2.0, 2.0, 1.5708
        self.call_service_sync(teleport1, t1_req, '/turtle1/teleport_absolute')

        teleport2 = self.create_client(TeleportAbsolute, '/turtle2/teleport_absolute')
        t2_req = TeleportAbsolute.Request()
        t2_req.x, t2_req.y, t2_req.theta = 5.0, 2.0, 1.5708
        self.call_service_sync(teleport2, t2_req, '/turtle2/teleport_absolute')

        teleport3 = self.create_client(TeleportAbsolute, '/turtle3/teleport_absolute')
        t3_req = TeleportAbsolute.Request()
        t3_req.x, t3_req.y, t3_req.theta = 8.0, 2.0, 1.5708
        self.call_service_sync(teleport3, t3_req, '/turtle3/teleport_absolute')

        self.get_logger().info("All 3 turtles positioned and initialized with distinct pen colors!")

    def publish_simultaneous(self, twist1, twist2, twist3, duration_sec, rate_hz=20):
        """Publishes velocity commands to all three turtles concurrently at fixed frequency."""
        steps = int(duration_sec * rate_hz)
        dt = 1.0 / rate_hz

        for _ in range(steps):
            self.pub_t1.publish(twist1)
            self.pub_t2.publish(twist2)
            self.pub_t3.publish(twist3)
            time.sleep(dt)

    def stop_all(self):
        """Sends zero velocity to all three turtles."""
        stop = Twist()
        for _ in range(5):
            self.pub_t1.publish(stop)
            self.pub_t2.publish(stop)
            self.pub_t3.publish(stop)
            time.sleep(0.02)

    def run_simultaneous_demo(self):
        """Executes a multi-phase simultaneous synchronized choreography."""
        self.setup_turtles()
        time.sleep(1.0)

        self.get_logger().info("Phase 1: Simultaneous forward drive...")
        cmd_fwd = Twist()
        cmd_fwd.linear.x = 2.0
        self.publish_simultaneous(cmd_fwd, cmd_fwd, cmd_fwd, duration_sec=2.5)

        self.stop_all()
        time.sleep(0.5)

        self.get_logger().info("Phase 2: Simultaneous synchronized turns...")
        cmd_turn = Twist()
        cmd_turn.angular.z = 1.5708  # 90 degrees/sec
        self.publish_simultaneous(cmd_turn, cmd_turn, cmd_turn, duration_sec=1.0)

        self.stop_all()
        time.sleep(0.5)

        self.get_logger().info("Phase 3: Simultaneous circle formations (varying radii)...")
        # Turtle1: tight fast circle
        c1 = Twist()
        c1.linear.x = 1.5
        c1.angular.z = 1.5

        # Turtle2: medium circle
        c2 = Twist()
        c2.linear.x = 2.0
        c2.angular.z = 1.0

        # Turtle3: counter-clockwise spiral/orbit
        c3 = Twist()
        c3.linear.x = 1.8
        c3.angular.z = -1.2

        self.publish_simultaneous(c1, c2, c3, duration_sec=4.0)

        self.stop_all()
        self.get_logger().info("Simultaneous choreography complete!")


def main(args=None):
    rclpy.init(args=args)
    node = None
    try:
        node = ThreeTurtleSimultaneous()
        node.run_simultaneous_demo()
    except KeyboardInterrupt:
        print("\nStopped by user.")
    finally:
        if node is not None:
            node.stop_all()
            node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
