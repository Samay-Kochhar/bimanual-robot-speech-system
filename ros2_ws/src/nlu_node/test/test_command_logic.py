from nlu_node.command_logic import interpret_nlu, validate_command


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
                entity('object', 'table', 53),
            ],
        )
    )

    assert command.source.size == 'small'
    assert command.source.elongated == 'long'
    assert command.source.xpos == 'left'
    assert command.source.ypos == 'front'
    assert command.target.size == 'big'
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
