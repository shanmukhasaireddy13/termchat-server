import os
import sys
import time
import cv2
import numpy as np
import rclpy

from rclpy.node import Node
from geometry_msgs.msg import Twist


class ArrowNavigation(Node):
    def __init__(self):
        super().__init__('arrow_navigation')

        self.publisher = self.create_publisher(
            Twist, '/cmd_vel_nav', 10
        )

        self.camera = cv2.VideoCapture(0)

        if not self.camera.isOpened():
            raise RuntimeError("Unable to open camera")

    def publish_velocity(self, linear=0.0, angular=0.0):
        msg = Twist()
        msg.linear.x = float(linear)
        msg.angular.z = float(angular)
        self.publisher.publish(msg)

    def detect_arrow(self, frame):
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)

        _, binary = cv2.threshold(
            blurred, 0, 255,
            cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU
        )

        contours, _ = cv2.findContours(
            binary,
            cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE
        )

        if not contours:
            return None, binary, None

        contour = max(contours, key=cv2.contourArea)

        if cv2.contourArea(contour) < 1000:
            return None, binary, None

        perimeter = cv2.arcLength(contour, True)
        approx = cv2.approxPolyDP(
            contour, 0.03 * perimeter, True
        )

        if len(approx) < 5 or len(approx) > 10:
            return None, binary, contour

        moments = cv2.moments(contour)

        if moments['m00'] == 0:
            return None, binary, contour

        cx = int(moments['m10'] / moments['m00'])
        cy = int(moments['m01'] / moments['m00'])

        vertices = approx.reshape(-1, 2)

        distances = np.sqrt(
            (vertices[:, 0] - cx) ** 2
            + (vertices[:, 1] - cy) ** 2
        )

        tip = vertices[np.argmax(distances)]
        dx = int(tip[0]) - cx
        dy = int(tip[1]) - cy

        # Accept only horizontal arrows.
        # Vertical arrows are not used in this experiment.
        if abs(dx) > abs(dy):
            direction = 'right' if dx > 0 else 'left'
        else:
            direction = None

        return direction, binary, contour

    def run(self):
        try:
            while rclpy.ok():
                ret, frame = self.camera.read()

                if not ret:
                    self.publish_velocity()
                    continue

                direction, binary, contour = self.detect_arrow(frame)

                if direction == 'left':
                    self.publish_velocity(angular=0.5)
                    label = 'LEFT - TURN LEFT'

                elif direction == 'right':
                    self.publish_velocity(angular=-0.5)
                    label = 'RIGHT - TURN RIGHT'

                else:
                    self.publish_velocity()
                    label = 'NO VALID LEFT/RIGHT ARROW - STOP'

                if contour is not None:
                    cv2.drawContours(
                        frame, [contour], -1, (0, 255, 0), 2
                    )

                self.get_logger().info(f"State: {label}")

                if os.environ.get("DISPLAY"):
                    try:
                        cv2.putText(
                            frame, label, (20, 40),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7,
                            (255, 255, 255), 2
                        )
                        cv2.imshow('LYRA Arrow Navigation', frame)
                        cv2.imshow('Arrow Threshold', binary)
                        if cv2.waitKey(1) & 0xFF == ord('q'):
                            break
                    except cv2.error:
                        pass
                else:
                    time.sleep(0.05)

        finally:
            self.publish_velocity()
            self.camera.release()
            cv2.destroyAllWindows()


def main(args=None):
    rclpy.init(args=args)
    node = None

    try:
        node = ArrowNavigation()
        node.run()

    except (RuntimeError, KeyboardInterrupt) as error:
        print(error)

    finally:
        if node is not None:
            node.destroy_node()

        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
