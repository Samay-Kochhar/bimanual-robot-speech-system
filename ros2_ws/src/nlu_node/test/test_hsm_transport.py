from nlu_node.hsm_transport import (
    action_error_message,
    normalize_hsm_mode,
    validate_user_task_xml,
)
from nlu_node.xml_builder import (
    build_give_xml,
    build_put_xml,
    build_stop_xml,
    ResolveRequest,
)


def test_hsm_mode_accepts_topic_and_action():
    assert normalize_hsm_mode('topic') == 'topic'
    assert normalize_hsm_mode(' ACTION ') == 'action'


def test_invalid_hsm_mode_falls_back_to_topic():
    assert normalize_hsm_mode('invalid') == 'topic'
    assert normalize_hsm_mode('') == 'topic'


def test_action_error_message_is_stable():
    assert action_error_message('server unavailable') == (
        'I could not send the robot command: server unavailable'
    )


def test_mock_hsm_accepts_generated_task_xml():
    put_xml = build_put_xml(
        ResolveRequest(cls='apple'),
        ResolveRequest(cls='bowl'),
        'in',
    )
    give_xml = build_give_xml(ResolveRequest(cls='block'))
    stop_xml = build_stop_xml()

    assert validate_user_task_xml(put_xml) == (True, 'Accepted put task.')
    assert validate_user_task_xml(give_xml) == (True, 'Accepted give task.')
    assert validate_user_task_xml(stop_xml) == (True, 'Accepted stop task.')


def test_mock_hsm_rejects_invalid_xml():
    success, message = validate_user_task_xml('<user_task')

    assert not success
    assert message.startswith('Invalid XML:')


def test_mock_hsm_rejects_unsupported_task_type():
    success, message = validate_user_task_xml(
        '<user_task type="dance"><STATUS /></user_task>'
    )

    assert not success
    assert message == 'Unsupported user_task type: dance.'
