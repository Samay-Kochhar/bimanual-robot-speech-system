from hsm_interfaces.action import ExecuteUserTask
import rclpy
from rclpy.action import ActionClient
from rclpy.node import Node
import requests
from std_msgs.msg import String

from .command_logic import (
    interpret_nlu,
    object_description,
    validate_command,
)
from .hsm_transport import (
    action_error_message,
    normalize_hsm_mode,
)
from .schema import FALLBACK_RESPONSE, SUPPORTED_INTENTS
from .xml_builder import build_give_xml, build_put_xml, build_stop_xml

RASA_URL = 'http://localhost:5005/model/parse'
DEFAULT_MIN_CONFIDENCE = 0.60
DEFAULT_HSM_ACTION_NAME = '/hsm/execute_user_task'


class NLUNode(Node):
    def __init__(self):
        super().__init__('nlu_node')
        self.declare_parameter('rasa_url', RASA_URL)
        self.declare_parameter('min_intent_confidence', DEFAULT_MIN_CONFIDENCE)
        self.declare_parameter('hsm_mode', 'topic')
        self.declare_parameter('hsm_action_name', DEFAULT_HSM_ACTION_NAME)
        self.declare_parameter('hsm_server_timeout', 1.0)
        self.rasa_url = self.get_parameter('rasa_url').value
        self.min_confidence = float(
            self.get_parameter('min_intent_confidence').value
        )
        requested_hsm_mode = self.get_parameter('hsm_mode').value
        self.hsm_mode = normalize_hsm_mode(requested_hsm_mode)
        self.hsm_action_name = self.get_parameter('hsm_action_name').value
        self.hsm_server_timeout = float(
            self.get_parameter('hsm_server_timeout').value
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
        self.hsm_action_client = ActionClient(
            self,
            ExecuteUserTask,
            self.hsm_action_name,
        )

        self.get_logger().info('NLU node subscribed to /asr/transcript.')
        self.get_logger().info(
            f'Rasa endpoint: {self.rasa_url}; minimum confidence: '
            f'{self.min_confidence:.2f}'
        )
        if self.hsm_mode != str(requested_hsm_mode).strip().lower():
            self.get_logger().warning(
                f'Invalid hsm_mode "{requested_hsm_mode}"; using topic mode.'
            )
        self.get_logger().info(f'HSM transport mode: {self.hsm_mode}.')

    def speak(self, text):
        msg = String()
        msg.data = text
        self.pub_tts.publish(msg)

    def publish_xml(self, xml):
        msg = String()
        msg.data = xml
        self.pub_xml.publish(msg)

    def dispatch_hsm(self, xml, success_response, task_name):
        if self.hsm_mode == 'topic':
            self.publish_xml(xml)
            self.speak(success_response)
            self.get_logger().info(
                f'{task_name} XML published to /hsm/xml.'
            )
            return

        if not self.hsm_action_client.wait_for_server(
            timeout_sec=self.hsm_server_timeout
        ):
            detail = 'the HSM action server is unavailable.'
            self.get_logger().error(detail)
            self.speak(action_error_message(detail))
            return

        goal = ExecuteUserTask.Goal()
        goal.xml = xml
        try:
            future = self.hsm_action_client.send_goal_async(
                goal,
                feedback_callback=self.on_hsm_feedback,
            )
            future.add_done_callback(
                lambda completed: self.on_hsm_goal_response(
                    completed,
                    success_response,
                    task_name,
                )
            )
        except Exception as error:
            self.get_logger().error(f'Failed to send HSM action goal: {error}')
            self.speak(
                action_error_message('the action goal could not be sent.')
            )

    def on_hsm_feedback(self, feedback_message):
        status = feedback_message.feedback.status
        self.get_logger().info(f'HSM action feedback: {status}')

    def on_hsm_goal_response(self, future, success_response, task_name):
        try:
            goal_handle = future.result()
        except Exception as error:
            self.get_logger().error(f'HSM action goal failed: {error}')
            self.speak(action_error_message('the action goal failed.'))
            return

        if not goal_handle.accepted:
            self.get_logger().warning('HSM action goal was rejected.')
            self.speak(action_error_message('the action goal was rejected.'))
            return

        self.get_logger().info(f'{task_name} action goal accepted.')
        result_future = goal_handle.get_result_async()
        result_future.add_done_callback(
            lambda completed: self.on_hsm_result(
                completed,
                success_response,
                task_name,
            )
        )

    def on_hsm_result(self, future, success_response, task_name):
        try:
            result = future.result().result
        except Exception as error:
            self.get_logger().error(f'HSM action result failed: {error}')
            self.speak(
                action_error_message('no action result was received.')
            )
            return

        if result.success:
            self.get_logger().info(
                f'{task_name} action succeeded: {result.message}'
            )
            self.speak(success_response)
            return

        self.get_logger().warning(
            f'{task_name} action failed: {result.message}'
        )
        self.speak(action_error_message(result.message))

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
            response = (
                f'Okay. Putting {object_description(command.source)} '
                f'{command.relation} {object_description(command.target)}.'
            )
            self.dispatch_hsm(xml, response, 'PUT')
            return

        if command.intent == 'give':
            xml = build_give_xml(command.source)
            response = (
                f'Okay. Giving you {object_description(command.source)}.'
            )
            self.dispatch_hsm(xml, response, 'GIVE')
            return

        if command.intent == 'stop':
            self.dispatch_hsm(
                build_stop_xml(),
                'Stopping the current robot task.',
                'STOP',
            )
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
