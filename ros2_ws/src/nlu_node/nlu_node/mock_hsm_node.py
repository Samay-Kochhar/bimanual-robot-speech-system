import rclpy
from rclpy.node import Node
from std_msgs.msg import String


class MockHSMNode(Node):
    """Log XML commands that would later be sent to the robot HSM."""

    def __init__(self):
        super().__init__('mock_hsm_node')
        self.subscription = self.create_subscription(
            String,
            '/hsm/xml',
            self.on_xml,
            10,
        )
        self.get_logger().info('Mock HSM listening on /hsm/xml.')

    def on_xml(self, message):
        xml = message.data.strip()
        if not xml:
            self.get_logger().warning('Received empty XML on /hsm/xml.')
            return
        self.get_logger().info(f'Received robot XML:\n{xml}')


def main(args=None):
    rclpy.init(args=args)
    node = MockHSMNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
