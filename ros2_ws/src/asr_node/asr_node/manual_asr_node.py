import sys
import time

import rclpy
from rclpy.node import Node
from rclpy.utilities import remove_ros_args
from std_msgs.msg import String


class ManualASRPublisher(Node):
    """Publish manually entered transcripts in place of a real ASR node."""

    def __init__(self):
        super().__init__('manual_asr')
        self.publisher = self.create_publisher(String, '/asr/transcript', 10)
        self.get_logger().info(
            'Manual ASR ready. Publishing transcripts to /asr/transcript.'
        )

    def publish_transcript(self, text):
        text = text.strip()
        if not text:
            self.get_logger().warning('Ignoring an empty transcript.')
            return

        message = String()
        message.data = text
        self.publisher.publish(message)
        self.get_logger().info(f'Published transcript: {text}')

    def wait_for_subscriber(self, timeout_seconds=2.0):
        deadline = time.monotonic() + timeout_seconds
        while self.count_subscribers('/asr/transcript') == 0:
            if time.monotonic() >= deadline:
                self.get_logger().warning(
                    'No /asr/transcript subscriber found; publishing anyway.'
                )
                return
            rclpy.spin_once(self, timeout_sec=0.1)


def main(args=None):
    rclpy.init(args=args)
    node = ManualASRPublisher()
    cli_args = remove_ros_args(args=sys.argv)[1:]

    try:
        if cli_args:
            node.wait_for_subscriber()
            node.publish_transcript(' '.join(cli_args))
            rclpy.spin_once(node, timeout_sec=0.5)
            return

        node.get_logger().info('Enter one command per line. Press Ctrl-D to exit.')
        while rclpy.ok():
            try:
                text = input('transcript> ')
            except EOFError:
                break
            node.publish_transcript(text)
            rclpy.spin_once(node, timeout_sec=0.1)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
