from dataclasses import dataclass
from xml.etree import ElementTree


@dataclass
class ResolveRequest:
    count: str = ''
    cls: str = ''
    color: str = ''
    elongated: str = ''
    pointing_time: str = '0'
    size: str = ''
    xpos: str = ''
    ypos: str = ''

    def attributes(self):
        """Return HSM attribute names and string values."""
        return {
            'count': self.count,
            'class': self.cls,
            'color': self.color,
            'elongated': self.elongated,
            'pointingTime': self.pointing_time,
            'size': self.size,
            'xpos': self.xpos,
            'ypos': self.ypos,
        }


def _string_attributes(attributes):
    return {
        key: '' if value is None else str(value)
        for key, value in attributes.items()
    }


def _resolve_element(parent, request):
    return ElementTree.SubElement(
        parent,
        'resolve_request',
        _string_attributes(request.attributes()),
    )


def _task_root(task_type, arm_pref=''):
    return ElementTree.Element(
        'user_task',
        {'type': task_type, 'armPref': arm_pref},
    )


def _finish(root):
    ElementTree.SubElement(
        root,
        'STATUS',
        {'origin': 'Submitter', 'value': 'initiated'},
    )
    ElementTree.indent(root, space='  ')
    body = ElementTree.tostring(root, encoding='unicode')
    return '<?xml version="1.0" encoding="UTF-8" standalone="no" ?>\n' + body


def resolve_request_xml(request):
    """Serialize one resolve request with XML-safe attributes."""
    element = ElementTree.Element(
        'resolve_request',
        _string_attributes(request.attributes()),
    )
    return ElementTree.tostring(element, encoding='unicode')


def build_put_xml(obj, target, relation, arm_pref=''):
    root = _task_root('put', arm_pref)
    _resolve_element(ElementTree.SubElement(root, 'object'), obj)
    target_element = ElementTree.SubElement(
        root,
        'target',
        {'relation': str(relation or '')},
    )
    _resolve_element(target_element, target)
    return _finish(root)


def build_give_xml(obj, arm_pref=''):
    root = _task_root('give', arm_pref)
    _resolve_element(ElementTree.SubElement(root, 'object'), obj)
    return _finish(root)


def build_stop_xml(arm_pref=''):
    return _finish(_task_root('stop', arm_pref))
