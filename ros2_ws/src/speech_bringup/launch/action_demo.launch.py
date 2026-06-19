from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    rasa_url = LaunchConfiguration('rasa_url')
    min_confidence = LaunchConfiguration('min_intent_confidence')

    return LaunchDescription(
        [
            DeclareLaunchArgument(
                'rasa_url',
                default_value='http://localhost:5005/model/parse',
                description='Rasa HTTP NLU parse endpoint.',
            ),
            DeclareLaunchArgument(
                'min_intent_confidence',
                default_value='0.60',
                description='Minimum accepted Rasa intent confidence.',
            ),
            Node(
                package='nlu_node',
                executable='nlu_node',
                name='nlu_node',
                output='screen',
                parameters=[
                    {
                        'rasa_url': rasa_url,
                        'min_intent_confidence': ParameterValue(
                            min_confidence,
                            value_type=float,
                        ),
                        'hsm_mode': 'action',
                    }
                ],
            ),
            Node(
                package='tts_node',
                executable='tts_node',
                name='tts_node',
                output='screen',
                parameters=[{'backend': 'print'}],
            ),
            Node(
                package='nlu_node',
                executable='mock_hsm_action',
                name='mock_hsm_action_server',
                output='screen',
            ),
        ]
    )
