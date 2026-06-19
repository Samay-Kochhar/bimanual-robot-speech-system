import ast
from pathlib import Path

LAUNCH_DIRECTORY = Path(__file__).parents[1] / 'launch'


def launch_source(filename):
    path = LAUNCH_DIRECTORY / filename
    return path.read_text(encoding='utf-8')


def string_literals(filename):
    tree = ast.parse(launch_source(filename))
    return {
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    }


def test_launch_files_are_valid_python():
    for filename in ('topic_demo.launch.py', 'action_demo.launch.py'):
        ast.parse(launch_source(filename))


def test_topic_demo_launches_expected_nodes():
    literals = string_literals('topic_demo.launch.py')

    assert {'mock_hsm', 'nlu_node', 'tts_node'} <= literals
    assert 'topic' in literals
    assert 'print' in literals


def test_action_demo_launches_expected_nodes():
    literals = string_literals('action_demo.launch.py')

    assert {'mock_hsm_action', 'nlu_node', 'tts_node'} <= literals
    assert 'action' in literals
    assert 'print' in literals


def test_launch_files_declare_expected_arguments():
    for filename in ('topic_demo.launch.py', 'action_demo.launch.py'):
        literals = string_literals(filename)
        assert 'rasa_url' in literals
        assert 'min_intent_confidence' in literals
        assert 'http://localhost:5005/model/parse' in literals
