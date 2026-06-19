#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from std_msgs.msg import String

from .backends import PrintTTSBackend, select_backend, TTSBackendError


class TTSNode(Node):
    def __init__(self):
        super().__init__('tts_node')
        self.declare_parameter('backend', 'auto')
        self.declare_parameter('command', '')

        preference = self.get_parameter('backend').value
        command = self.get_parameter('command').value
        selection = select_backend(preference, command)
        self.backend = selection.backend

        self.sub = self.create_subscription(
            String,
            '/tts/speak',
            self.on_speak,
            10,
        )
        self.get_logger().info(selection.message)
        self.get_logger().info(
            f'TTS node listening on /tts/speak with backend '
            f'"{self.backend.name}".'
        )

    def on_speak(self, msg):
        text = msg.data.strip()
        if not text:
            return

        self.get_logger().info(f'TTS request: {text}')
        try:
            self.backend.speak(text)
        except TTSBackendError as error:
            self.get_logger().error(str(error))
            self.get_logger().warning('Switching to print TTS fallback.')
            self.backend = PrintTTSBackend()
            self.backend.speak(text)


def main(args=None):
    rclpy.init(args=args)
    node = TTSNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
