from xml.etree import ElementTree

from nlu_node.command_logic import interpret_nlu, validate_command
from nlu_node.xml_builder import build_put_xml


def entity(name, value, start):
    return {
        'entity': name,
        'value': value,
        'start': start,
        'end': start + len(value),
    }


def rasa_result(intent, confidence, entities=None):
    return {
        'intent': {'name': intent, 'confidence': confidence},
        'entities': entities or [],
    }


def put_xml_from_entities(entities):
    command = interpret_nlu(rasa_result('put', 0.98, entities))
    xml = build_put_xml(command.source, command.target, command.relation)
    return command, ElementTree.fromstring(xml)


def test_put_maps_source_target_and_relation():
    command = interpret_nlu(
        rasa_result(
            'put',
            0.98,
            [
                entity('quantifier', 'the', 4),
                entity('color', 'red', 8),
                entity('object', 'apple', 12),
                entity('relation', 'in', 18),
                entity('quantifier', 'the', 21),
                entity('color', 'blue', 25),
                entity('object', 'bowl', 30),
            ],
        )
    )

    assert command.source.count == 'the'
    assert command.source.color == 'red'
    assert command.source.cls == 'apple'
    assert command.relation == 'in'
    assert command.target.count == 'the'
    assert command.target.color == 'blue'
    assert command.target.cls == 'bowl'
    assert validate_command(command) == (True, '')


def test_regression_put_red_apple_in_blue_bowl():
    command, root = put_xml_from_entities([
        entity('quantifier', 'the', 4),
        entity('color', 'red', 8),
        entity('object', 'apple', 12),
        entity('relation', 'in', 18),
        entity('quantifier', 'the', 21),
        # Reproduce the observed Rasa misclassification.
        entity('elongated', 'blue', 25),
        entity('object', 'bowl', 30),
    ])

    target = root.find('./target/resolve_request')
    assert command.target.color == 'blue'
    assert command.target.elongated == ''
    assert target.attrib['color'] == 'blue'
    assert target.attrib['elongated'] == ''


def test_regression_put_long_red_apple_in_small_blue_bowl():
    command, root = put_xml_from_entities([
        entity('quantifier', 'the', 4),
        entity('elongated', 'long', 8),
        entity('color', 'red', 13),
        entity('object', 'apple', 17),
        entity('relation', 'in', 23),
        entity('quantifier', 'the', 26),
        entity('color', 'small', 30),
        entity('elongated', 'blue', 36),
        entity('object', 'bowl', 41),
    ])

    source = root.find('./object/resolve_request')
    target = root.find('./target/resolve_request')
    assert command.source.elongated == 'long'
    assert command.source.color == 'red'
    assert command.target.size == 'small'
    assert command.target.color == 'blue'
    assert command.target.elongated == ''
    assert source.attrib['elongated'] == 'long'
    assert source.attrib['color'] == 'red'
    assert target.attrib['size'] == 'small'
    assert target.attrib['color'] == 'blue'
    assert target.attrib['elongated'] == ''


def test_regression_put_green_block_on_yellow_box():
    command, root = put_xml_from_entities([
        entity('quantifier', 'the', 4),
        entity('color', 'green', 8),
        entity('object', 'block', 14),
        entity('relation', 'on', 20),
        entity('quantifier', 'the', 23),
        entity('object', 'yellow', 27),
        entity('object', 'box', 34),
    ])

    target = root.find('./target/resolve_request')
    assert command.source.color == 'green'
    assert command.target.color == 'yellow'
    assert command.target.size == ''
    assert target.attrib['color'] == 'yellow'
    assert target.attrib['size'] == ''


def test_put_maps_size_shape_and_positions_to_correct_object():
    command = interpret_nlu(
        rasa_result(
            'put',
            0.95,
            [
                entity('quantifier', 'one', 4),
                entity('size', 'small', 8),
                entity('elongated', 'long', 14),
                entity('xpos', 'left', 19),
                entity('ypos', 'front', 24),
                entity('object', 'block', 30),
                entity('relation', 'right of', 36),
                entity('quantifier', 'the', 45),
                entity('size', 'big', 49),
                entity('color', 'blue', 53),
                entity('elongated', 'short', 58),
                entity('xpos', 'right', 64),
                entity('ypos', 'back', 70),
                entity('object', 'table', 75),
            ],
        )
    )

    assert command.source.size == 'small'
    assert command.source.elongated == 'long'
    assert command.source.xpos == 'left'
    assert command.source.ypos == 'front'
    assert command.target.count == 'the'
    assert command.target.size == 'big'
    assert command.target.color == 'blue'
    assert command.target.elongated == 'short'
    assert command.target.xpos == 'right'
    assert command.target.ypos == 'back'
    assert command.relation == 'right'


def test_demonstrative_sets_nonzero_pointing_placeholder():
    command = interpret_nlu(
        rasa_result(
            'put',
            0.99,
            [
                entity('quantifier', 'this', 4),
                entity('object', 'object', 9),
                entity('relation', 'in', 16),
                entity('quantifier', 'the', 19),
                entity('object', 'box', 23),
            ],
        )
    )

    assert command.source.count == 'this'
    assert command.source.pointing_time != '0'
    assert command.target.pointing_time == '0'


def test_give_requires_an_object():
    command = interpret_nlu(rasa_result('give', 0.97))
    valid, question = validate_command(command)

    assert not valid
    assert question == 'Which object should I give you?'


def test_put_missing_target_requires_clarification():
    command = interpret_nlu(
        rasa_result(
            'put',
            0.96,
            [
                entity('object', 'apple', 4),
                entity('relation', 'in', 10),
            ],
        )
    )
    valid, question = validate_command(command)

    assert not valid
    assert question == 'What is the target object?'


def test_stop_is_valid_without_entities():
    command = interpret_nlu(rasa_result('stop', 1.0))
    assert validate_command(command) == (True, '')


def test_unsupported_intent_is_rejected():
    command = interpret_nlu(rasa_result('greet', 0.99))
    assert validate_command(command) == (False, 'unsupported')
