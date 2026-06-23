from dataclasses import dataclass, field

from .schema import (
    ATTRIBUTE_VALUE_TYPES,
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


def _resolve_request(entities):
    count = normalize(
        QUANTIFIER_ALIASES,
        _first_value(entities, 'quantifier'),
    )
    pointing_time = '0'
    if count in {'this', 'that'}:
        # TODO: Replace this nonzero marker with the real pointing timestamp.
        pointing_time = POINTING_TIME_PLACEHOLDER

    return ResolveRequest(
        count=count,
        cls=_first_value(entities, 'object'),
        color=_first_value(entities, 'color'),
        elongated=_first_value(entities, 'elongated'),
        pointing_time=pointing_time,
        size=_first_value(entities, 'size'),
        xpos=_first_value(entities, 'xpos'),
        ypos=_first_value(entities, 'ypos'),
    )


def _partition_put_entities(entities):
    source = []
    target = []
    relation = ''
    after_relation = False

    ordered = sorted(
        entities,
        key=lambda entity: entity.get('start', len(source) + len(target)),
    )
    for entity in ordered:
        if _normalized_entity_name(entity) == 'relation' and not relation:
            relation = normalize(RELATION_ALIASES, _entity_value(entity))
            after_relation = True
            continue
        if after_relation:
            target.append(entity)
        else:
            source.append(entity)

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
    if intent == 'put':
        source_entities, target_entities, relation = _partition_put_entities(
            entities
        )
        return RobotCommand(
            intent=intent,
            confidence=confidence,
            source=_resolve_request(source_entities),
            target=_resolve_request(target_entities),
            relation=relation,
        )

    return RobotCommand(
        intent=intent,
        confidence=confidence,
        source=_resolve_request(entities),
    )


def validate_command(command):
    """Return whether a supported command has all execution-critical fields."""
    if command.intent not in SUPPORTED_INTENTS:
        return False, 'unsupported'

    fields = {
        'object_src': command.source.cls,
        'object_tgt': command.target.cls,
        'relation': command.relation,
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
