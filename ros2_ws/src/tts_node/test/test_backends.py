import subprocess

import pytest

from tts_node.backends import (
    CommandTTSBackend,
    find_command,
    PrintTTSBackend,
    select_backend,
    TTSBackendError,
)


def fake_which(installed):
    def lookup(command):
        return installed.get(command)

    return lookup


def test_print_backend_emits_clear_output():
    output = []
    backend = PrintTTSBackend(output.append)

    backend.speak('hello robot')

    assert output == ['TTS OUTPUT: hello robot']


def test_auto_selects_first_available_command():
    selection = select_backend(
        'auto',
        which=fake_which({'espeak-ng': '/usr/bin/espeak-ng'}),
    )

    assert isinstance(selection.backend, CommandTTSBackend)
    assert selection.backend.executable == '/usr/bin/espeak-ng'


def test_explicit_command_is_preferred():
    selection = select_backend(
        'command',
        command='custom-say',
        which=fake_which({'custom-say': '/opt/bin/custom-say'}),
    )

    assert selection.backend.executable == '/opt/bin/custom-say'


def test_missing_command_falls_back_to_print():
    selection = select_backend(
        'command',
        command='missing-say',
        which=fake_which({}),
    )

    assert isinstance(selection.backend, PrintTTSBackend)
    assert 'fallback' in selection.message


def test_kokoro_is_optional_and_falls_back():
    selection = select_backend('kokoro', which=fake_which({}))

    assert isinstance(selection.backend, PrintTTSBackend)
    assert 'not configured' in selection.message


def test_find_command_uses_priority_order():
    executable = find_command(
        which=fake_which(
            {
                'spd-say': '/usr/bin/spd-say',
                'espeak': '/usr/bin/espeak',
            }
        )
    )

    assert executable == '/usr/bin/spd-say'


def test_command_backend_passes_text_without_shell():
    calls = []

    def runner(args, check, timeout):
        calls.append((args, check, timeout))

    backend = CommandTTSBackend('/usr/bin/spd-say', runner=runner)
    backend.speak('hello; not a shell command')

    assert calls == [
        (
            ['/usr/bin/spd-say', 'hello; not a shell command'],
            True,
            30,
        )
    ]


def test_command_failure_raises_backend_error():
    def runner(args, check, timeout):
        raise subprocess.CalledProcessError(1, args)

    backend = CommandTTSBackend('/usr/bin/spd-say', runner=runner)

    with pytest.raises(TTSBackendError):
        backend.speak('hello')
