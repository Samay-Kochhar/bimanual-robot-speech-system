#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from std_msgs.msg import String


class TTSNode(Node):
    def __init__(self):
        super().__init__('tts_node')
        self.sub = self.create_subscription(
            String,
            '/tts/speak',
            self.on_speak,
            10,
        )
        self.get_logger().info('TTS mock listening on /tts/speak.')

    def on_speak(self, msg: String):
        text = msg.data.strip()
        if not text:
            return
        self.get_logger().info(f'TTS OUTPUT: {text}')


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
