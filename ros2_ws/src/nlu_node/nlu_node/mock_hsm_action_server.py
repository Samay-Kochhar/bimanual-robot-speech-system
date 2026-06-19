from hsm_interfaces.action import ExecuteUserTask
import rclpy
from rclpy.action import ActionServer
from rclpy.node import Node

from .hsm_transport import validate_user_task_xml


ACTION_NAME = '/hsm/execute_user_task'


class MockHSMActionServer(Node):
    """Mock action server that validates and logs HSM XML goals."""

    def __init__(self):
        super().__init__('mock_hsm_action_server')
        self.server = ActionServer(
            self,
            ExecuteUserTask,
            ACTION_NAME,
            self.execute,
        )
        self.get_logger().info(
            f'Mock HSM action server listening on {ACTION_NAME}.'
        )

    def execute(self, goal_handle):
        xml = goal_handle.request.xml.strip()
        self.get_logger().info(f'Received HSM action XML:\n{xml}')

        feedback = ExecuteUserTask.Feedback()
        feedback.status = 'validating XML'
        goal_handle.publish_feedback(feedback)

        success, message = validate_user_task_xml(xml)
        result = ExecuteUserTask.Result()
        result.success = success
        result.message = message

        if success:
            feedback.status = 'mock execution complete'
            goal_handle.publish_feedback(feedback)
            goal_handle.succeed()
            self.get_logger().info(message)
        else:
            goal_handle.abort()
            self.get_logger().warning(message)
        return result

    def destroy_node(self):
        self.server.destroy()
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = MockHSMActionServer()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
