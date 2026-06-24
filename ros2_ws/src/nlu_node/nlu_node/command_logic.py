from dataclasses import dataclass, field
import re

from .schema import (
    ATTRIBUTE_VALUE_TYPES,
    CANONICAL_RELATIONS,
    CLARIFY,
    normalize,
    QUANTIFIER_ALIASES,
    RELATION_ALIASES,
    REQUIRED,
    SUPPORTED_INTENTS,
)
from .xml_builder import ResolveRequest

POINTING_TIME_PLACEHOLDER = '1'


@dataclass
class RobotCommand:
    intent: str = 'unknown'
    confidence: float = 0.0
    source: ResolveRequest = field(default_factory=ResolveRequest)
    target: ResolveRequest = field(default_factory=ResolveRequest)
    relation: str = ''


def _entity_name(entity):
    return str(entity.get('entity', '')).strip().lower()


def _entity_value(entity):
    return str(entity.get('value', '')).strip().lower()


def _entity_start(entity):
    try:
        return int(entity.get('start'))
    except (TypeError, ValueError):
        return None


def _entity_end(entity):
    try:
        return int(entity.get('end'))
    except (TypeError, ValueError):
        return None


def _normalized_entity_name(entity):
    """Correct descriptive entity labels using professor-grammar values."""
    name = _entity_name(entity)
    if name == 'relation':
        return name

    value = _entity_value(entity)
    for attribute_name, values in ATTRIBUTE_VALUE_TYPES.items():
        if value in values:
            return attribute_name
    return name


def _first_value(entities, name):
    for entity in entities:
        if _normalized_entity_name(entity) == name:
            return _entity_value(entity)
    return ''


def _phrase_text(text, entities):
    if not text or not entities:
        return ''

    starts = [
        start
        for start in (_entity_start(entity) for entity in entities)
        if start is not None
    ]
    ends = [
        end
        for end in (_entity_end(entity) for entity in entities)
        if end is not None
    ]
    if not starts or not ends:
        return ''
    return text[min(starts):max(ends)].lower()


def _first_value_from_text(text, entities, name):
    phrase = _phrase_text(text, entities)
    if not phrase:
        return ''

    for value in ATTRIBUTE_VALUE_TYPES.get(name, ()):
        if re.search(r'\b' + re.escape(value) + r'\b', phrase):
            return value
    return ''


def _first_value_or_text(text, entities, name):
    return (
        _first_value(entities, name)
        or _first_value_from_text(text, entities, name)
    )


def _resolve_request(entities, text=''):
    count = normalize(
        QUANTIFIER_ALIASES,
        _first_value_or_text(text, entities, 'quantifier'),
    )
    pointing_time = '0'
    if count in {'this', 'that'}:
        # TODO: Replace this nonzero marker with the real pointing timestamp.
        pointing_time = POINTING_TIME_PLACEHOLDER

    return ResolveRequest(
        count=count,
        cls=_first_value(entities, 'object'),
        color=_first_value_or_text(text, entities, 'color'),
        elongated=_first_value_or_text(text, entities, 'elongated'),
        pointing_time=pointing_time,
        size=_first_value_or_text(text, entities, 'size'),
        xpos=_first_value_or_text(text, entities, 'xpos'),
        ypos=_first_value_or_text(text, entities, 'ypos'),
    )


def _canonical_relation(value):
    relation = normalize(RELATION_ALIASES, value)
    if relation in CANONICAL_RELATIONS:
        return relation
    return ''


def _relation_patterns():
    return sorted(
        RELATION_ALIASES,
        key=lambda value: (-len(value), value),
    )


def _relation_candidates(text):
    lowered = str(text or '').lower()
    candidates = []
    for phrase in _relation_patterns():
        pattern = r'\b' + re.escape(phrase) + r'\b'
        for match in re.finditer(pattern, lowered):
            relation = _canonical_relation(phrase)
            if relation:
                candidates.append(
                    (match.start(), match.end(), relation, phrase)
                )
    return sorted(candidates, key=lambda item: (item[0], -len(item[3])))


def _object_spans(entities):
    spans = []
    for entity in entities:
        if _normalized_entity_name(entity) != 'object':
            continue
        start = _entity_start(entity)
        end = _entity_end(entity)
        if start is not None and end is not None:
            spans.append((start, end))
    return sorted(spans)


def _recover_relation(text, entities):
    candidates = _relation_candidates(text)
    object_spans = _object_spans(entities)
    if len(object_spans) >= 2:
        source_start = object_spans[0][0]
        target_start = object_spans[1][0]
        bounded = [
            candidate
            for candidate in candidates
            if source_start <= candidate[0] and candidate[1] <= target_start
        ]
        if bounded:
            return bounded[0]

    for entity in entities:
        if _entity_name(entity) != 'relation':
            continue
        relation = _canonical_relation(_entity_value(entity))
        if relation:
            start = _entity_start(entity)
            end = _entity_end(entity)
            if start is not None and end is not None:
                return start, end, relation, _entity_value(entity)

    return None


def _trim_entity_value(entity, end):
    start = _entity_start(entity)
    if start is None or end <= start:
        return None

    value = _entity_value(entity)
    text_length = end - start
    trimmed = value[:text_length].strip()
    if not trimmed:
        return None

    updated = dict(entity)
    updated['value'] = trimmed
    updated['end'] = end
    return updated


def _fallback_relation_span(entities):
    for entity in entities:
        if _entity_name(entity) == 'relation':
            start = _entity_start(entity)
            end = _entity_end(entity)
            if start is not None and end is not None:
                return start, end
    return None


def _partition_put_entities(entities, text=''):
    source = []
    target = []
    relation = ''
    relation_match = _recover_relation(text, entities)

    if relation_match:
        relation_start, relation_end, relation, _phrase = relation_match
    else:
        span = _fallback_relation_span(entities)
        if span is None:
            return list(entities), [], ''
        relation_start, relation_end = span

    ordered = sorted(
        entities,
        key=lambda entity: (
            _entity_start(entity)
            if _entity_start(entity) is not None
            else len(source) + len(target)
        ),
    )
    for entity in ordered:
        name = _normalized_entity_name(entity)
        start = _entity_start(entity)
        end = _entity_end(entity)

        if _entity_name(entity) == 'relation':
            continue
        if start is None or end is None:
            if relation_match:
                target.append(entity)
            else:
                source.append(entity)
            continue
        if end <= relation_start:
            source.append(entity)
            continue
        if start >= relation_end:
            target.append(entity)
            continue
        if name == 'object' and start < relation_start:
            trimmed = _trim_entity_value(entity, relation_start)
            if trimmed:
                source.append(trimmed)

    return source, target, relation


def interpret_nlu(nlu):
    """Convert a Rasa /model/parse result into a normalized robot command."""
    intent_data = nlu.get('intent') or {}
    intent = str(intent_data.get('name', 'unknown')).strip().lower()
    try:
        confidence = float(intent_data.get('confidence', 0.0))
    except (TypeError, ValueError):
        confidence = 0.0

    entities = list(nlu.get('entities') or [])
    text = str(nlu.get('text') or '')
    if intent == 'put':
        source_entities, target_entities, relation = _partition_put_entities(
            entities,
            text,
        )
        return RobotCommand(
            intent=intent,
            confidence=confidence,
            source=_resolve_request(source_entities, text),
            target=_resolve_request(target_entities, text),
            relation=relation,
        )

    return RobotCommand(
        intent=intent,
        confidence=confidence,
        source=_resolve_request(entities, text),
    )


def validate_command(command):
    """Return whether a supported command has all execution-critical fields."""
    if command.intent not in SUPPORTED_INTENTS:
        return False, 'unsupported'

    relation = command.relation if command.relation in CANONICAL_RELATIONS else ''
    fields = {
        'object_src': command.source.cls,
        'object_tgt': command.target.cls,
        'relation': relation,
    }
    for field_name in REQUIRED[command.intent]:
        if not fields.get(field_name):
            question = CLARIFY.get(
                (command.intent, field_name),
                'Could you clarify the command?',
            )
            return False, question
    return True, ''


def object_description(request):
    """Create a compact phrase for acknowledgement speech."""
    parts = [
        request.count,
        request.size,
        request.elongated,
        request.color,
        request.cls,
    ]
    description = ' '.join(part for part in parts if part)
    return description or 'object'


def put_confirmation_relation_phrase(relation):
    """Return natural speech for a canonical put relation."""
    phrases = {
        'in': 'in',
        'on': 'on',
        'left': 'to the left of',
        'right': 'to the right of',
        'front': 'in front of',
        'behind': 'behind',
    }
    return phrases.get(str(relation or '').strip().lower(), relation)
