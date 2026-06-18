import rclpy
from rclpy.node import Node
import requests
from std_msgs.msg import String

from .command_logic import (
    interpret_nlu,
    object_description,
    validate_command,
)
from .schema import FALLBACK_RESPONSE, SUPPORTED_INTENTS
from .xml_builder import build_give_xml, build_put_xml, build_stop_xml

RASA_URL = 'http://localhost:5005/model/parse'
DEFAULT_MIN_CONFIDENCE = 0.60


class NLUNode(Node):
    def __init__(self):
        super().__init__('nlu_node')
        self.declare_parameter('rasa_url', RASA_URL)
        self.declare_parameter('min_intent_confidence', DEFAULT_MIN_CONFIDENCE)
        self.rasa_url = self.get_parameter('rasa_url').value
        self.min_confidence = float(
            self.get_parameter('min_intent_confidence').value
        )
        self.http = requests.Session()
        self.http.trust_env = False

        self.sub = self.create_subscription(
            String,
            '/asr/transcript',
            self.on_transcript,
            10,
        )
        self.pub_tts = self.create_publisher(String, '/tts/speak', 10)
        self.pub_xml = self.create_publisher(String, '/hsm/xml', 10)

        self.get_logger().info('NLU node subscribed to /asr/transcript.')
        self.get_logger().info(
            f'Rasa endpoint: {self.rasa_url}; minimum confidence: '
            f'{self.min_confidence:.2f}'
        )

    def speak(self, text):
        msg = String()
        msg.data = text
        self.pub_tts.publish(msg)

    def publish_xml(self, xml):
        msg = String()
        msg.data = xml
        self.pub_xml.publish(msg)

    def call_rasa(self, text):
        resp = self.http.post(
            self.rasa_url,
            json={'text': text},
            timeout=5,
        )
        resp.raise_for_status()
        return resp.json()

    def on_transcript(self, msg):
        text = msg.data.strip()
        if not text:
            return

        self.get_logger().info(f'Received transcript: {text}')

        try:
            nlu = self.call_rasa(text)
        except Exception as e:
            self.get_logger().error(f'Rasa call failed: {e}')
            self.speak("Sorry, I can't reach the language understanding module.")
            return

        command = interpret_nlu(nlu)
        self.get_logger().info(
            f'Rasa result: intent={command.intent}, '
            f'confidence={command.confidence:.3f}, '
            f'source={command.source.cls}, target={command.target.cls}, '
            f'relation={command.relation}'
        )

        if (
            command.intent not in SUPPORTED_INTENTS
            or command.confidence < self.min_confidence
        ):
            self.get_logger().warning('Unsupported or low-confidence command.')
            self.speak(FALLBACK_RESPONSE)
            return

        ok, question = validate_command(command)

        if not ok:
            self.get_logger().info(f'Publishing clarification: {question}')
            self.speak(question)
            return

        if command.intent == 'put':
            xml = build_put_xml(
                command.source,
                command.target,
                command.relation,
            )
            self.publish_xml(xml)
            self.speak(
                f'Okay. Putting {object_description(command.source)} '
                f'{command.relation} {object_description(command.target)}.'
            )
            self.get_logger().info('PUT XML published to /hsm/xml.')
            return

        if command.intent == 'give':
            xml = build_give_xml(command.source)
            self.publish_xml(xml)
            self.speak(
                f'Okay. Giving you {object_description(command.source)}.'
            )
            self.get_logger().info('GIVE XML published to /hsm/xml.')
            return

        if command.intent == 'stop':
            self.publish_xml(build_stop_xml())
            self.speak('Stopping the current robot task.')
            self.get_logger().info('STOP XML published to /hsm/xml.')
            return


def main(args=None):
    rclpy.init(args=args)
    node = NLUNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
