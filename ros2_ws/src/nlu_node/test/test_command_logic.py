from xml.etree import ElementTree

from nlu_node.command_logic import (
    interpret_nlu,
    put_confirmation_relation_phrase,
    validate_command,
)
from nlu_node.xml_builder import build_put_xml


def entity(name, value, start):
    return {
        'entity': name,
        'value': value,
        'start': start,
        'end': start + len(value),
    }


def rasa_result(intent, confidence, entities=None, text=''):
    return {
        'text': text,
        'intent': {'name': intent, 'confidence': confidence},
        'entities': entities or [],
    }


def put_xml_from_entities(entities, text=''):
    command = interpret_nlu(rasa_result('put', 0.98, entities, text))
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


def test_regression_put_red_apple_into_blue_bowl():
    command, root = put_xml_from_entities(
        [
            entity('quantifier', 'the', 4),
            entity('color', 'red', 8),
            entity('object', 'apple', 12),
            entity('relation', 'into', 18),
            entity('quantifier', 'the', 23),
            # Reproduce the observed Rasa misclassification.
            entity('elongated', 'blue', 27),
            entity('object', 'bowl', 32),
        ],
        'put the red apple into the blue bowl',
    )

    target = root.find('./target/resolve_request')
    assert command.relation == 'in'
    assert command.target.cls == 'bowl'
    assert command.target.color == 'blue'
    assert command.target.elongated == ''
    assert target.attrib['class'] == 'bowl'
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
    command, root = put_xml_from_entities(
        [
            entity('quantifier', 'the', 4),
            entity('color', 'green', 8),
            entity('object', 'block', 14),
            entity('relation', 'on', 20),
            entity('quantifier', 'the', 23),
            # Reproduce live Rasa output: yellow is omitted entirely.
            entity('object', 'box', 34),
        ],
        'put the green block on the yellow box',
    )

    target = root.find('./target/resolve_request')
    assert command.source.color == 'green'
    assert command.target.cls == 'box'
    assert command.target.color == 'yellow'
    assert command.target.elongated == ''
    assert command.target.size == ''
    assert target.attrib['class'] == 'box'
    assert target.attrib['color'] == 'yellow'
    assert target.attrib['elongated'] == ''
    assert target.attrib['size'] == ''


def test_regression_put_yellow_box_on_green_block():
    command, root = put_xml_from_entities(
        [
            entity('quantifier', 'the', 4),
            # Reproduce live Rasa output: yellow is omitted entirely.
            entity('object', 'box', 15),
            entity('relation', 'on', 19),
            entity('quantifier', 'the', 22),
            entity('color', 'green', 26),
            entity('object', 'block', 32),
        ],
        'put the yellow box on the green block',
    )

    source = root.find('./object/resolve_request')
    target = root.find('./target/resolve_request')
    assert command.source.cls == 'box'
    assert command.source.color == 'yellow'
    assert command.target.cls == 'block'
    assert command.target.color == 'green'
    assert source.attrib['class'] == 'box'
    assert source.attrib['color'] == 'yellow'
    assert target.attrib['class'] == 'block'
    assert target.attrib['color'] == 'green'


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


def test_relation_inside_normalizes_to_in():
    command, root = put_xml_from_entities(
        [
            entity('quantifier', 'the', 4),
            entity('color', 'red', 8),
            entity('object', 'apple', 12),
            entity('relation', 'inside', 18),
            entity('quantifier', 'the', 25),
            entity('color', 'blue', 29),
            entity('object', 'bowl', 34),
        ],
        'put the red apple inside the blue bowl',
    )

    assert validate_command(command) == (True, '')
    assert command.relation == 'in'
    assert root.find('./target').attrib['relation'] == 'in'


def test_relation_onto_normalizes_to_on():
    command, root = put_xml_from_entities(
        [
            entity('quantifier', 'the', 4),
            entity('color', 'red', 8),
            entity('object', 'block', 12),
            entity('relation', 'onto', 18),
            entity('quantifier', 'the', 23),
            entity('color', 'green', 27),
            entity('object', 'cube', 33),
        ],
        'put the red block onto the green cube',
    )

    assert validate_command(command) == (True, '')
    assert command.relation == 'on'
    assert root.find('./target').attrib['relation'] == 'on'


def test_relation_left_of_normalizes_to_left():
    command, root = put_xml_from_entities(
        [
            entity('quantifier', 'the', 4),
            entity('color', 'red', 8),
            entity('object', 'block', 12),
            entity('relation', 'left', 18),
            entity('relation', 'of', 23),
            entity('quantifier', 'the', 26),
            entity('color', 'green', 30),
            entity('object', 'cube', 36),
        ],
        'put the red block left of the green cube',
    )

    assert validate_command(command) == (True, '')
    assert command.relation == 'left'
    assert root.find('./target').attrib['relation'] == 'left'


def test_relation_to_the_left_of_recovers_left():
    command, root = put_xml_from_entities(
        [
            entity('quantifier', 'the', 4),
            entity('color', 'red', 8),
            entity('object', 'block', 12),
            entity('relation', 'to', 18),
            entity('quantifier', 'the', 21),
            entity('relation', 'left', 25),
            entity('relation', 'of', 30),
            entity('quantifier', 'the', 33),
            entity('color', 'green', 37),
            entity('object', 'cube', 43),
        ],
        'put the red block to the left of the green cube',
    )

    assert validate_command(command) == (True, '')
    assert command.relation == 'left'
    assert command.target.cls == 'cube'
    assert command.target.color == 'green'
    assert root.find('./target').attrib['relation'] == 'left'


def test_relation_right_of_recovers_right_when_rasa_swallowed_right():
    command, root = put_xml_from_entities(
        [
            entity('quantifier', 'the', 4),
            entity('color', 'red', 8),
            entity('object', 'block right', 12),
            entity('relation', 'of', 24),
            entity('quantifier', 'the', 27),
            entity('color', 'green', 31),
            entity('object', 'cube', 37),
        ],
        'put the red block right of the green cube',
    )

    assert validate_command(command) == (True, '')
    assert command.source.cls == 'block'
    assert command.relation == 'right'
    assert command.target.cls == 'cube'
    assert root.find('./target').attrib['relation'] == 'right'


def test_relation_in_front_of_recovers_front():
    command, root = put_xml_from_entities(
        [
            entity('quantifier', 'the', 4),
            entity('color', 'red', 8),
            entity('object', 'block', 12),
            entity('relation', 'in front', 18),
            entity('relation', 'of', 27),
            entity('quantifier', 'the', 30),
            entity('color', 'green', 34),
            entity('object', 'cube', 40),
        ],
        'put the red block in front of the green cube',
    )

    assert validate_command(command) == (True, '')
    assert command.relation == 'front'
    assert root.find('./target').attrib['relation'] == 'front'


def test_malformed_relation_fragment_of_is_not_executable():
    command = interpret_nlu(
        rasa_result(
            'put',
            0.98,
            [
                entity('quantifier', 'the', 4),
                entity('color', 'red', 8),
                entity('object', 'block', 12),
                entity('relation', 'of', 18),
                entity('quantifier', 'the', 21),
                entity('color', 'green', 25),
                entity('object', 'cube', 31),
            ],
            'put the red block of the green cube',
        )
    )

    valid, question = validate_command(command)
    assert not valid
    assert question == (
        'Where should I put it: in, on, left, right, front, or behind?'
    )


def test_put_confirmation_relation_phrases_are_natural():
    assert put_confirmation_relation_phrase('in') == 'in'
    assert put_confirmation_relation_phrase('on') == 'on'
    assert put_confirmation_relation_phrase('left') == 'to the left of'
    assert put_confirmation_relation_phrase('right') == 'to the right of'
    assert put_confirmation_relation_phrase('front') == 'in front of'
    assert put_confirmation_relation_phrase('behind') == 'behind'


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
