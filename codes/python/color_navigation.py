import cv2
import numpy as np
import rclpy

from rclpy.node import Node
from geometry_msgs.msg import Twist


class ColorNavigation(Node):
    def __init__(self):
        super().__init__('color_navigation')

        self.publisher = self.create_publisher(
            Twist, '/cmd_vel_nav', 10
        )

        self.camera = cv2.VideoCapture(0)

        if not self.camera.isOpened():
            raise RuntimeError("Unable to open camera")

        self.color_ranges = {
            'green': (
                np.array([35, 60, 40]),
                np.array([90, 255, 255])
            ),
            'yellow': (
                np.array([20, 80, 80]),
                np.array([35, 255, 255])
            ),
            'red1': (
                np.array([0, 100, 80]),
                np.array([10, 255, 255])
            ),
            'red2': (
                np.array([170, 100, 80]),
                np.array([180, 255, 255])
            )
        }

    def publish_velocity(self, linear=0.0, angular=0.0):
        msg = Twist()
        msg.linear.x = float(linear)
        msg.angular.z = float(angular)
        self.publisher.publish(msg)

    def detect_color(self, hsv):
        masks = {}

        for color in ['green', 'yellow']:
            lower, upper = self.color_ranges[color]
            masks[color] = cv2.inRange(hsv, lower, upper)

        lower, upper = self.color_ranges['red1']
        red1 = cv2.inRange(hsv, lower, upper)

        lower, upper = self.color_ranges['red2']
        red2 = cv2.inRange(hsv, lower, upper)

        masks['red'] = cv2.bitwise_or(red1, red2)

        detected_color = None
        largest_area = 800

        # Give red priority when multiple colors are visible.
        for color in ['red', 'green', 'yellow']:
            contours, _ = cv2.findContours(
                masks[color],
                cv2.RETR_EXTERNAL,
                cv2.CHAIN_APPROX_SIMPLE
            )

            for contour in contours:
                area = cv2.contourArea(contour)

                if area > largest_area:
                    largest_area = area
                    detected_color = color

        return detected_color

    def run(self):
        try:
            while rclpy.ok():
                ret, frame = self.camera.read()

                if not ret:
                    self.publish_velocity()
                    continue

                hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
                color = self.detect_color(hsv)

                if color == 'green':
                    self.publish_velocity(linear=0.3)
                    label = 'GREEN - FORWARD'

                elif color == 'yellow':
                    self.publish_velocity(linear=-0.3)
                    label = 'YELLOW - BACKWARD'

                elif color == 'red':
                    self.publish_velocity()
                    label = 'RED - STOP'

                else:
                    self.publish_velocity()
                    label = 'NO COLOR - STOP'

                cv2.putText(
                    frame, label, (20, 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8,
                    (255, 255, 255), 2
                )

                cv2.imshow('LYRA Color Navigation', frame)

                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break

        finally:
            self.publish_velocity()
            self.camera.release()
            cv2.destroyAllWindows()


def main(args=None):
    rclpy.init(args=args)
    node = None

    try:
        node = ColorNavigation()
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
