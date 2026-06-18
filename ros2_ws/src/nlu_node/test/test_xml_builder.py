from xml.etree import ElementTree

from nlu_node.xml_builder import (
    build_give_xml,
    build_put_xml,
    build_stop_xml,
    ResolveRequest,
)


def test_put_xml_maps_all_attributes():
    source = ResolveRequest(
        count='this',
        cls='apple',
        color='red',
        elongated='long',
        pointing_time='1',
        size='small',
        xpos='left',
        ypos='front',
    )
    target = ResolveRequest(count='the', cls='bowl', color='blue')

    root = ElementTree.fromstring(build_put_xml(source, target, 'in'))
    source_xml = root.find('./object/resolve_request')
    target_xml = root.find('./target/resolve_request')

    assert root.attrib['type'] == 'put'
    assert source_xml.attrib == {
        'count': 'this',
        'class': 'apple',
        'color': 'red',
        'elongated': 'long',
        'pointingTime': '1',
        'size': 'small',
        'xpos': 'left',
        'ypos': 'front',
    }
    assert root.find('./target').attrib['relation'] == 'in'
    assert target_xml.attrib['class'] == 'bowl'
    assert target_xml.attrib['color'] == 'blue'


def test_xml_values_are_escaped_safely():
    xml = build_give_xml(
        ResolveRequest(
            cls='apple & pear',
            color='red "special"',
        )
    )

    assert 'apple &amp; pear' in xml
    assert '&quot;' in xml
    parsed = ElementTree.fromstring(xml)
    request = parsed.find('./object/resolve_request')
    assert request.attrib['class'] == 'apple & pear'
    assert request.attrib['color'] == 'red "special"'


def test_give_xml_has_object_and_status():
    root = ElementTree.fromstring(
        build_give_xml(ResolveRequest(count='one', cls='block'))
    )

    assert root.attrib['type'] == 'give'
    assert root.find('./object/resolve_request').attrib['count'] == 'one'
    assert root.find('./STATUS').attrib['value'] == 'initiated'


def test_stop_xml_uses_same_task_style():
    root = ElementTree.fromstring(build_stop_xml())

    assert root.attrib == {'type': 'stop', 'armPref': ''}
    assert root.find('./object') is None
    assert root.find('./target') is None
    assert root.find('./STATUS').attrib == {
        'origin': 'Submitter',
        'value': 'initiated',
    }
