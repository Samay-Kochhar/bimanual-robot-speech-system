REQUIRED = {
    'put': ['object_src', 'relation', 'object_tgt'],
    'give': ['object_src'],
    'stop': [],
}

CLARIFY = {
    ('put', 'object_src'): 'Which object should I put?',
    ('put', 'relation'): (
        'Where should I put it: in, on, left, right, front, or behind?'
    ),
    ('put', 'object_tgt'): 'What is the target object?',
    ('give', 'object_src'): 'Which object should I give you?',
}

SUPPORTED_INTENTS = frozenset(REQUIRED)

FALLBACK_RESPONSE = 'Sorry, I did not understand a supported robot command.'

RELATION_ALIASES = {
    'in': 'in',
    'into': 'in',
    'on': 'on',
    'onto': 'on',
    'on top of': 'on',
    'left': 'left',
    'left of': 'left',
    'to the left of': 'left',
    'right': 'right',
    'right of': 'right',
    'to the right of': 'right',
    'front': 'front',
    'front of': 'front',
    'in front of': 'front',
    'behind': 'behind',
}

QUANTIFIER_ALIASES = {
    'a': 'a',
    'an': 'an',
    'one': 'one',
    'the': 'the',
    'all': 'all',
    'any': 'any',
    'this': 'this',
    'that': 'that',
}

ATTRIBUTE_VALUE_TYPES = {
    'color': frozenset({'red', 'green', 'blue', 'yellow'}),
    'size': frozenset({'small', 'big'}),
    'elongated': frozenset({'short', 'long', 'elongated'}),
    'xpos': frozenset({'left', 'right'}),
    'ypos': frozenset({'front', 'back'}),
    'quantifier': frozenset(QUANTIFIER_ALIASES),
}


def normalize(mapping, value):
    """Normalize a case-insensitive entity value with an alias mapping."""
    cleaned = str(value or '').strip().lower()
    return mapping.get(cleaned, cleaned)
