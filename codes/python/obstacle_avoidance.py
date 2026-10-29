#!/usr/bin/env python3
"""
BeetleBot Autonomous Obstacle Avoidance (ROS 2 Jazzy)
Subscribes to /scan (LiDAR) and publishes to /cmd_vel_nav (Twist).
Implements reverse-before-turn collision avoidance behavior.
"""

import math
import time
import numpy as np
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import LaserScan
from geometry_msgs.msg import Twist

class ObstacleAvoidanceNode(Node):
    def __init__(self):
        super().__init__('obstacle_avoidance_node')

        # Configured parameters from BeetleBot guide
        self.safe_distance  = 0.50  # m
        self.front_distance = 0.45  # m
        self.move_speed     = 0.20  # m/s
        self.reverse_speed  = 0.12  # m/s
        self.turn_speed     = 0.40  # rad/s
        self.reverse_time   = 0.80  # s

        self.reversing_until = 0.0

        self.publisher = self.create_publisher(Twist, '/cmd_vel_nav', 10)
        self.subscription = self.create_subscription(
            LaserScan,
            '/scan',
            self.scan_callback,
            10
        )
        self.get_logger().info("Obstacle Avoidance Node Started.")

    def publish_twist(self, linear_x=0.0, angular_z=0.0):
        twist = Twist()
        twist.linear.x = float(linear_x)
        twist.angular.z = float(angular_z)
        self.publisher.publish(twist)

    def scan_callback(self, msg: LaserScan):
        now = time.time()
        if now < self.reversing_until:
            self.publish_twist(linear_x=-self.reverse_speed, angular_z=0.0)
            return

        ranges = np.array(msg.ranges, dtype=np.float32)
        angles = msg.angle_min + np.arange(len(ranges)) * msg.angle_increment
        angles = (angles + math.pi) % (2 * math.pi) - math.pi

        valid = np.isfinite(ranges) & (ranges > max(msg.range_min, 0.12)) & (ranges < msg.range_max)
        r = ranges[valid]
        a = angles[valid]

        if len(r) == 0:
            self.publish_twist(0.0, 0.0)
            return

        front_mask = np.abs(a) < 0.45             # Front sector (+/- 25 deg)
        left_mask = (a >= 0.45) & (a <= 1.57)     # Left sector
        right_mask = (a <= -0.45) & (a >= -1.57)  # Right sector

        front_dist = float(r[front_mask].min()) if front_mask.any() else 5.0
        left_dist = float(r[left_mask].min()) if left_mask.any() else 5.0
        right_dist = float(r[right_mask].min()) if right_mask.any() else 5.0

        self.get_logger().info(f"Front: {front_dist:.2f} m | Left: {left_dist:.2f} m | Right: {right_dist:.2f} m")

        # 1. Obstacle directly ahead: reverse for 0.8s
        if front_dist < self.front_distance:
            self.get_logger().warn("Obstacle directly ahead! Reversing...")
            self.reversing_until = now + self.reverse_time
            self.publish_twist(linear_x=-self.reverse_speed, angular_z=0.0)

        # 2. Front partially blocked: turn toward clearer side
        elif front_dist < self.safe_distance:
            if left_dist > right_dist:
                self.publish_twist(linear_x=0.0, angular_z=self.turn_speed)
            else:
                self.publish_twist(linear_x=0.0, angular_z=-self.turn_speed)

        # 3. Front is clear: move forward
        else:
            self.publish_twist(linear_x=self.move_speed, angular_z=0.0)

    def stop(self):
        for _ in range(5):
            self.publish_twist(0.0, 0.0)
            time.sleep(0.02)

def main(args=None):
    rclpy.init(args=args)
    node = ObstacleAvoidanceNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.stop()
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()

if __name__ == '__main__':
    main()
