from xml.etree import ElementTree

HSM_MODES = frozenset({'topic', 'action'})
SUPPORTED_TASK_TYPES = frozenset({'put', 'give', 'stop'})


def normalize_hsm_mode(value):
    """Return a supported HSM mode, defaulting invalid values to topic."""
    mode = str(value or '').strip().lower()
    if mode in HSM_MODES:
        return mode
    return 'topic'


def action_error_message(detail):
    """Create a stable spoken error for failed HSM action delivery."""
    detail = str(detail or '').strip()
    if detail:
        return f'I could not send the robot command: {detail}'
    return 'I could not send the robot command.'


def validate_user_task_xml(xml):
    """Validate the minimal XML contract accepted by the mock HSM."""
    try:
        root = ElementTree.fromstring(xml)
    except ElementTree.ParseError as error:
        return False, f'Invalid XML: {error}'

    if root.tag != 'user_task':
        return False, 'Root element must be user_task.'
    task_type = root.attrib.get('type', '')
    if task_type not in SUPPORTED_TASK_TYPES:
        return False, (
            f'Unsupported user_task type: {task_type or "missing"}.'
        )
    return True, f'Accepted {task_type} task.'
