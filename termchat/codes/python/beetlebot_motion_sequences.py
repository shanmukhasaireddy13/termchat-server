#!/usr/bin/env python3
"""
beetlebot_motion_sequences.py
==============================
ROS 2 Jazzy automated movement sequences, arming controls, and hardware testing
for the Veerobot Beetle Bot (Lyra Platform).

Publishes to target topic: /cmd_vel_nav
Services: /lyra/arm, /lyra/disarm

Available Sequences:
  1. forward          - Drive forward (0.3 m/s for 5s) + 1.5s forced stop
  2. backward         - Drive backward (-0.3 m/s for 5s) + 1.5s forced stop
  3. stop             - Emergency flood stop (forces halt at 20 Hz)
  4. advance_seq      - Forward 5s -> Stop 1.5s -> Backward 5s -> Stop 2s
  5. square           - Square path sequence (4 sides: Drive -> Stop -> Turn -> Stop)
  6. arm              - Call /lyra/arm service to enable motor safety gates
  7. disarm           - Call /lyra/disarm service to drop software gates
  8. teleop           - Interactive keyboard teleop remapped to /cmd_vel_nav
"""

import sys
import time
import subprocess
import signal

try:
    import rclpy
    from rclpy.node import Node
    from geometry_msgs.msg import Twist
    from std_srvs.srv import Trigger
    ROS2_AVAILABLE = True
except ImportError:
    ROS2_AVAILABLE = False


class LyraMotionRunner(Node if ROS2_AVAILABLE else object):
    def __init__(self):
        if not ROS2_AVAILABLE:
            raise RuntimeError("ROS 2 environment (rclpy) is not available. Please source /opt/ros/jazzy/setup.bash.")
        super().__init__('lyra_motion_runner')
        self.cmd_pub = self.create_publisher(Twist, '/cmd_vel_nav', 10)
        self.get_logger().info("Lyra Motion Runner initialized. Target topic: /cmd_vel_nav")

    def publish_cmd(self, linear_x=0.0, angular_z=0.0, duration=1.0, rate_hz=10):
        """Publishes constant linear and angular velocities for a given duration."""
        msg = Twist()
        msg.linear.x = float(linear_x)
        msg.linear.y = 0.0
        msg.linear.z = 0.0
        msg.angular.x = 0.0
        msg.angular.y = 0.0
        msg.angular.z = float(angular_z)

        interval = 1.0 / rate_hz
        ticks = int(duration * rate_hz)

        for _ in range(ticks):
            self.cmd_pub.publish(msg)
            time.sleep(interval)

    def emergency_stop(self):
        """Sends emergency flood halt commands at 20 Hz."""
        self.get_logger().info("[HALT] Emergency Flood Stop active.")
        self.publish_cmd(linear_x=0.0, angular_z=0.0, duration=2.0, rate_hz=20)

    def arm_robot(self):
        """Calls /lyra/arm service."""
        client = self.create_client(Trigger, '/lyra/arm')
        self.get_logger().info("Waiting for /lyra/arm service...")
        if not client.wait_for_service(timeout_sec=3.0):
            self.get_logger().error("Service /lyra/arm is not available. Ensure 'robot.launch.py' is running in Terminal 1.")
            return False

        req = Trigger.Request()
        future = client.call_async(req)
        rclpy.spin_until_future_complete(self, future, timeout_sec=3.0)
        if future.result():
            res = future.result()
            self.get_logger().info(f"[ARM SUCCESS] {res.message}")
            return True
        else:
            self.get_logger().error("[ARM FAILED] Service call failed.")
            return False

    def disarm_robot(self):
        """Calls /lyra/disarm service."""
        client = self.create_client(Trigger, '/lyra/disarm')
        self.get_logger().info("Waiting for /lyra/disarm service...")
        if not client.wait_for_service(timeout_sec=3.0):
            self.get_logger().error("Service /lyra/disarm is not available.")
            return False

        req = Trigger.Request()
        future = client.call_async(req)
        rclpy.spin_until_future_complete(self, future, timeout_sec=3.0)
        if future.result():
            res = future.result()
            self.get_logger().info(f"[DISARM SUCCESS] {res.message}")
            return True
        else:
            self.get_logger().error("[DISARM FAILED] Service call failed.")
            return False

    def run_forward(self):
        self.get_logger().info("--- SEQUENCE 1: MOVE FORWARD (5s + 1.5s forced stop) ---")
        self.get_logger().info("Moving FORWARD at 0.3 m/s for 5.0 seconds...")
        self.publish_cmd(linear_x=0.3, angular_z=0.0, duration=5.0, rate_hz=10)
        self.get_logger().info("Applying FORCED STOP (1.5s)...")
        self.publish_cmd(linear_x=0.0, angular_z=0.0, duration=1.5, rate_hz=10)
        self.get_logger().info("Sequence complete.")

    def run_backward(self):
        self.get_logger().info("--- SEQUENCE 2: MOVE BACKWARD (5s + 1.5s forced stop) ---")
        self.get_logger().info("Moving BACKWARD at -0.3 m/s for 5.0 seconds...")
        self.publish_cmd(linear_x=-0.3, angular_z=0.0, duration=5.0, rate_hz=10)
        self.get_logger().info("Applying FORCED STOP (1.5s)...")
        self.publish_cmd(linear_x=0.0, angular_z=0.0, duration=1.5, rate_hz=10)
        self.get_logger().info("Sequence complete.")

    def run_advanced_sequence(self):
        self.get_logger().info("--- SEQUENCE 4: ADVANCED SEQUENCE (FORWARD -> STOP -> BACKWARD -> STOP) ---")
        self.get_logger().info("[1/4] Forward at 0.3 m/s for 5.0s...")
        self.publish_cmd(linear_x=0.3, angular_z=0.0, duration=5.0, rate_hz=10)
        self.get_logger().info("[2/4] Forced Stop for 1.5s...")
        self.publish_cmd(linear_x=0.0, angular_z=0.0, duration=1.5, rate_hz=10)
        self.get_logger().info("[3/4] Backward at -0.3 m/s for 5.0s...")
        self.publish_cmd(linear_x=-0.3, angular_z=0.0, duration=5.0, rate_hz=10)
        self.get_logger().info("[4/4] Final Forced Stop for 2.0s...")
        self.publish_cmd(linear_x=0.0, angular_z=0.0, duration=2.0, rate_hz=10)
        self.get_logger().info("Advanced sequence complete.")

    def run_square(self):
        self.get_logger().info("--- SEQUENCE 5: SQUARE PATH SEQUENCE (4 SIDES) ---")
        for side in range(1, 5):
            self.get_logger().info(f"[Side {side}/4] Driving forward (3.0s at 0.3 m/s)...")
            self.publish_cmd(linear_x=0.3, angular_z=0.0, duration=3.0, rate_hz=10)

            self.get_logger().info(f"[Side {side}/4] Braking / Stopping (1.0s)...")
            self.publish_cmd(linear_x=0.0, angular_z=0.0, duration=1.0, rate_hz=10)

            self.get_logger().info(f"[Side {side}/4] Turning 90 deg (2.0s at 0.5 rad/s)...")
            self.publish_cmd(linear_x=0.0, angular_z=0.5, duration=2.0, rate_hz=10)

            self.get_logger().info(f"[Side {side}/4] Settling / Stopping (1.0s)...")
            self.publish_cmd(linear_x=0.0, angular_z=0.0, duration=1.0, rate_hz=10)

        # Final stop
        self.publish_cmd(linear_x=0.0, angular_z=0.0, duration=1.5, rate_hz=10)
        self.get_logger().info("Square path sequence complete.")


def run_keyboard_teleop():
    """Launches teleop_twist_keyboard remapped to /cmd_vel_nav."""
    cmd = [
        "ros2", "run", "teleop_twist_keyboard", "teleop_twist_keyboard",
        "--ros-args", "-r", "cmd_vel:=cmd_vel_nav"
    ]
    print("\n" + "=" * 65)
    print("      BEETLE BOT JAZZY - KEYBOARD TELEOPERATION")
    print("=" * 65)
    print("Target Topic: /cmd_vel_nav")
    print("\nControls Reference:")
    print("   [ q ]  [ w ]  [ e ]      q/z : Speed +/- 10%")
    print("   [ a ]  [ s ]  [ d ]      w/x : Linear speed +/- 10%")
    print("                            e/c : Angular speed +/- 10%")
    print("   [ i ]  [ o ]  [ p ]      i   : Forward")
    print("   [ j ]  [ k ]  [ l ]      ,   : Backward")
    print("   [ m ]  [ , ]  [ . ]      j   : Left   |   l : Right")
    print("                            k   : STOP Completely")
    print("=" * 65 + "\n")
    try:
        subprocess.call(cmd)
    except KeyboardInterrupt:
        print("\nTeleoperation halted.")


def main(action="list"):
    act = action.lower().strip()
    if act in ("teleop", "keyboard", "manual"):
        run_keyboard_teleop()
        return 0

    if not ROS2_AVAILABLE:
        print("[Error] ROS 2 Jazzy is not sourced. Please run:")
        print("  source /opt/ros/jazzy/setup.bash")
        print("  source ~/lyra_ws/install/setup.bash")
        return 1

    rclpy.init()
    node = LyraMotionRunner()

    def sig_handler(sig, frame):
        print("\n[Safety Interrupt] Halting motors immediately...")
        node.emergency_stop()
        node.destroy_node()
        rclpy.shutdown()
        sys.exit(0)

    signal.signal(signal.SIGINT, sig_handler)

    try:
        if act in ("forward", "fwd"):
            node.run_forward()
        elif act in ("backward", "back", "rev"):
            node.run_backward()
        elif act in ("stop", "halt", "emergency_stop"):
            node.emergency_stop()
        elif act in ("seq", "advance_seq", "advanced", "patrol"):
            node.run_advanced_sequence()
        elif act in ("square", "box"):
            node.run_square()
        elif act in ("arm", "arm_robot"):
            node.arm_robot()
        elif act in ("disarm", "disarm_robot"):
            node.disarm_robot()
        else:
            print("Available BeetleBot commands:")
            print("  arm         - Close safety gates and enable wheel motor controllers")
            print("  disarm      - Electronic emergency disarm")
            print("  forward     - Move forward 5s + forced stop")
            print("  backward    - Move backward 5s + forced stop")
            print("  stop        - Emergency flood stop (20 Hz zero-velocity vector)")
            print("  square      - Square path sequence (4 sides: Drive -> Stop -> Turn -> Stop)")
            print("  seq         - Forward 5s -> Stop -> Backward 5s -> Stop")
            print("  teleop      - Launch keyboard teleoperation remapped to /cmd_vel_nav")
    finally:
        try:
            node.emergency_stop()
            node.destroy_node()
        except Exception:
            pass
        if rclpy.ok():
            rclpy.shutdown()

    return 0


if __name__ == "__main__":
    choice = sys.argv[1] if len(sys.argv) > 1 else "forward"
    sys.exit(main(choice))
