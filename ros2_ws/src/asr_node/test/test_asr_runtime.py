from types import SimpleNamespace

from asr_node.asr_runtime import audio_rms
from asr_node.asr_runtime import detect_cuda_compute_types
from asr_node.asr_runtime import fallback_choices
from asr_node.asr_runtime import join_segments
from asr_node.asr_runtime import pcm16_to_float32
from asr_node.asr_runtime import resolve_runtime

import numpy as np
import pytest


class FakeCTranslate2:
    @staticmethod
    def get_cuda_device_count():
        return 1

    @staticmethod
    def get_supported_compute_types(device):
        assert device == 'cuda'
        return {'float16', 'float32'}


def test_detect_cuda_compute_types():
    assert detect_cuda_compute_types(FakeCTranslate2()) == {
        'float16',
        'float32',
    }


def test_detect_cuda_can_report_pascal_compute_types():
    fake = SimpleNamespace(
        get_cuda_device_count=lambda: 1,
        get_supported_compute_types=lambda device: {
            'float32', 'int8', 'int8_float32'
        },
    )
    assert detect_cuda_compute_types(fake) == {
        'float32', 'int8', 'int8_float32'
    }


def test_auto_runtime_prefers_medium_cuda_float16():
    choice = resolve_runtime('auto', 'auto', 'auto', {'float16', 'float32'})
    assert choice.model_size == 'medium'
    assert choice.device == 'cuda'
    assert choice.compute_type == 'float16'


def test_auto_runtime_uses_int8_float32_on_pascal_gpu():
    choice = resolve_runtime(
        'auto', 'auto', 'auto', {'float32', 'int8', 'int8_float32'}
    )
    assert choice.model_size == 'medium'
    assert choice.device == 'cuda'
    assert choice.compute_type == 'int8_float32'


def test_auto_runtime_uses_small_cpu_int8_without_cuda():
    choice = resolve_runtime('auto', 'auto', 'auto', set())
    assert choice.model_size == 'small'
    assert choice.device == 'cpu'
    assert choice.compute_type == 'int8'


def test_explicit_unavailable_cuda_is_rejected():
    with pytest.raises(ValueError, match='CUDA was requested'):
        resolve_runtime('small', 'cuda', 'float16', set())


def test_medium_cuda_fallback_order():
    primary = resolve_runtime('auto', 'auto', 'auto', {'float16'})
    choices = fallback_choices(primary)
    assert [(c.model_size, c.device, c.compute_type) for c in choices] == [
        ('medium', 'cuda', 'float16'),
        ('small', 'cuda', 'float16'),
        ('small', 'cpu', 'int8'),
    ]


def test_cpu_runtime_has_no_duplicate_fallback():
    primary = resolve_runtime('small', 'cpu', 'int8', set())
    assert fallback_choices(primary) == [primary]


def test_pcm16_conversion_and_rms():
    pcm = np.array([-32768, 0, 16384, 32767], dtype=np.int16)
    samples = pcm16_to_float32(pcm.tobytes())
    assert samples.dtype == np.float32
    assert samples.tolist() == pytest.approx([-1.0, 0.0, 0.5, 32767 / 32768])
    assert audio_rms(samples) > 0.0


def test_empty_audio_rms_is_zero():
    assert audio_rms(np.array([], dtype=np.float32)) == 0.0


def test_join_segments_produces_final_text():
    segments = [
        SimpleNamespace(text=' Put the red apple'),
        SimpleNamespace(text=' in the blue bowl. '),
    ]
    assert join_segments(segments) == 'Put the red apple in the blue bowl.'


def test_join_segments_ignores_empty_text():
    segments = [SimpleNamespace(text=' '), SimpleNamespace(text='stop')]
    assert join_segments(segments) == 'stop'
