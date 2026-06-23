"""Runtime selection and audio helpers for Faster-Whisper ASR."""

from dataclasses import dataclass


SUPPORTED_DEVICES = {'auto', 'cpu', 'cuda'}


@dataclass(frozen=True)
class RuntimeChoice:
    """A concrete Faster-Whisper model runtime configuration."""

    model_size: str
    device: str
    compute_type: str


def detect_cuda_device_count(ctranslate2_module=None):
    """Return the number of NVIDIA devices visible to CTranslate2."""
    if ctranslate2_module is None:
        try:
            import ctranslate2 as ctranslate2_module
        except (ImportError, OSError):
            return 0

    try:
        return int(ctranslate2_module.get_cuda_device_count())
    except (RuntimeError, OSError):
        return 0


def detect_cuda_compute_types(ctranslate2_module=None, library_loader=None):
    """Return compute types exposed by CTranslate2 for the first CUDA GPU."""
    if ctranslate2_module is None:
        try:
            if library_loader is None:
                from ctypes import CDLL as library_loader

            library_loader('libcublas.so.12')
            library_loader('libcudnn.so.9')

            import ctranslate2 as ctranslate2_module
        except (ImportError, OSError):
            return frozenset()

    try:
        if detect_cuda_device_count(ctranslate2_module) < 1:
            return frozenset()
        compute_types = ctranslate2_module.get_supported_compute_types('cuda')
        return frozenset(compute_types)
    except (RuntimeError, OSError):
        return frozenset()


def cuda_runtime_needs_setup(requested_device, device_count, compute_types):
    """Return whether GPU mode is blocked by missing runtime libraries."""
    requested_device = str(requested_device).strip().lower()
    return (
        requested_device in {'auto', 'cuda'}
        and int(device_count) > 0
        and not compute_types
    )


def preferred_cuda_compute_type(compute_types):
    """Select the fastest suitable CUDA type, preferring float16."""
    for compute_type in ('float16', 'int8_float16', 'int8_float32', 'float32'):
        if compute_type in compute_types:
            return compute_type
    return None


def resolve_runtime(model_size, device, compute_type, cuda_compute_types):
    """Resolve auto values into a concrete model/device/compute choice."""
    model_size = str(model_size).strip().lower()
    device = str(device).strip().lower()
    compute_type = str(compute_type).strip().lower()
    cuda_compute_types = frozenset(cuda_compute_types)
    cuda_compute_type = preferred_cuda_compute_type(cuda_compute_types)

    if device not in SUPPORTED_DEVICES:
        raise ValueError('device must be one of: auto, cpu, cuda')

    if device == 'auto':
        device = 'cuda' if cuda_compute_type else 'cpu'
    elif device == 'cuda' and not cuda_compute_type:
        raise ValueError(
            'CUDA was requested but is unavailable to CTranslate2'
        )

    if not model_size or model_size == 'auto':
        model_size = 'medium' if device == 'cuda' else 'small'

    if not compute_type or compute_type == 'auto':
        compute_type = cuda_compute_type if device == 'cuda' else 'int8'
    elif device == 'cuda' and compute_type not in cuda_compute_types:
        supported = ', '.join(sorted(cuda_compute_types))
        raise ValueError(
            f'CUDA compute_type {compute_type} is unsupported; use: {supported}'
        )

    return RuntimeChoice(model_size, device, compute_type)


def fallback_choices(primary, allow_cpu_fallback=True):
    """Return ordered, unique runtime choices for graceful fallback."""
    choices = [primary]

    if primary.device == 'cuda' and primary.model_size != 'small':
        choices.append(
            RuntimeChoice('small', 'cuda', primary.compute_type)
        )

    if allow_cpu_fallback and primary.device == 'cuda':
        choices.append(RuntimeChoice('small', 'cpu', 'int8'))

    unique = []
    for choice in choices:
        if choice not in unique:
            unique.append(choice)
    return unique


def pcm16_to_float32(audio_bytes, numpy_module=None):
    """Convert mono signed 16-bit PCM bytes to normalized float32 samples."""
    if numpy_module is None:
        import numpy as numpy_module

    samples = numpy_module.frombuffer(audio_bytes, dtype=numpy_module.int16)
    return samples.astype(numpy_module.float32) / 32768.0


def audio_rms(samples, numpy_module=None):
    """Compute RMS amplitude for a normalized audio array."""
    if numpy_module is None:
        import numpy as numpy_module

    if samples.size == 0:
        return 0.0
    return float(numpy_module.sqrt(numpy_module.mean(samples * samples)))


def join_segments(segments):
    """Join Faster-Whisper segment text into one final transcript."""
    return ' '.join(
        segment.text.strip()
        for segment in segments
        if getattr(segment, 'text', '').strip()
    ).strip()
