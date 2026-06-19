from abc import ABC, abstractmethod
from dataclasses import dataclass
import shutil
import subprocess


COMMAND_CANDIDATES = ('spd-say', 'espeak-ng', 'espeak', 'say')


class TTSBackendError(RuntimeError):
    """Raised when a TTS backend cannot speak an utterance."""


class TTSBackend(ABC):
    """Interface implemented by replaceable text-to-speech backends."""

    name = 'unknown'

    @abstractmethod
    def speak(self, text):
        """Speak or otherwise handle one non-empty utterance."""


class PrintTTSBackend(TTSBackend):
    """Fallback backend that prints text without producing audio."""

    name = 'print'

    def __init__(self, output=print):
        self.output = output

    def speak(self, text):
        self.output(f'TTS OUTPUT: {text}')


class CommandTTSBackend(TTSBackend):
    """Speak by passing text as an argument to a local executable."""

    def __init__(self, executable, runner=subprocess.run):
        self.executable = executable
        self.runner = runner
        self.name = f'command:{executable}'

    def speak(self, text):
        try:
            self.runner(
                [self.executable, text],
                check=True,
                timeout=30,
            )
        except (OSError, subprocess.SubprocessError) as error:
            raise TTSBackendError(
                f'Command TTS backend failed: {error}'
            ) from error


@dataclass(frozen=True)
class BackendSelection:
    backend: TTSBackend
    message: str


def find_command(command='', which=shutil.which):
    """Find an explicit command or the first supported installed command."""
    if command:
        return which(command)

    for candidate in COMMAND_CANDIDATES:
        executable = which(candidate)
        if executable:
            return executable
    return None


def select_backend(preference='auto', command='', which=shutil.which):
    """Select a requested backend and always return a usable fallback."""
    requested = str(preference or 'auto').strip().lower()

    if requested == 'print':
        return BackendSelection(
            PrintTTSBackend(),
            'Print TTS backend selected.',
        )

    if requested in {'auto', 'command'}:
        executable = find_command(command=command, which=which)
        if executable:
            return BackendSelection(
                CommandTTSBackend(executable),
                f'Command TTS backend selected: {executable}',
            )

        detail = f' "{command}"' if command else ''
        return BackendSelection(
            PrintTTSBackend(),
            f'No command TTS backend{detail} found; using print fallback.',
        )

    if requested == 'kokoro':
        return BackendSelection(
            PrintTTSBackend(),
            'Kokoro is not configured; using print fallback.',
        )

    return BackendSelection(
        PrintTTSBackend(),
        f'Unknown TTS backend "{requested}"; using print fallback.',
    )
