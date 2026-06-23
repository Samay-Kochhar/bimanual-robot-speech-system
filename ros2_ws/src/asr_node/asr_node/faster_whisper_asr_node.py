"""ROS 2 microphone ASR node backed by Faster-Whisper."""

import threading

from asr_node.asr_runtime import audio_rms
from asr_node.asr_runtime import cuda_runtime_needs_setup
from asr_node.asr_runtime import detect_cuda_compute_types
from asr_node.asr_runtime import detect_cuda_device_count
from asr_node.asr_runtime import fallback_choices
from asr_node.asr_runtime import join_segments
from asr_node.asr_runtime import pcm16_to_float32
from asr_node.asr_runtime import resolve_runtime

import rclpy
from rclpy.node import Node
from std_msgs.msg import String


class ASRStartupError(RuntimeError):
    """Raised when an ASR dependency or runtime resource is unavailable."""


class FasterWhisperASRNode(Node):
    """Record fixed microphone windows and publish final transcripts."""

    def __init__(self):
        """Initialize parameters, model, microphone, and worker."""
        super().__init__('faster_whisper_asr')

        self.declare_parameter('model_size', 'auto')
        self.declare_parameter('device', 'auto')
        self.declare_parameter('compute_type', 'auto')
        self.declare_parameter('allow_cpu_fallback', True)
        self.declare_parameter('record_seconds', 5.0)
        self.declare_parameter('sample_rate', 16000)
        self.declare_parameter('input_device_index', -1)
        self.declare_parameter('language', 'en')
        self.declare_parameter('beam_size', 5)
        self.declare_parameter('min_audio_rms', 0.003)

        self.publisher = self.create_publisher(String, '/asr/transcript', 10)
        self._stop_event = threading.Event()
        self._audio = None
        self._pyaudio = None
        self._model = None
        self._runtime = None
        self._worker = None

        self._read_parameters()
        self._load_dependencies_and_model()
        self._validate_microphone()

        self.get_logger().info(
            'Faster-Whisper ASR ready: '
            f'model={self._runtime.model_size}, '
            f'device={self._runtime.device}, '
            f'compute_type={self._runtime.compute_type}, '
            f'record_seconds={self.record_seconds:.1f}, '
            f'topic=/asr/transcript'
        )

        self._worker = threading.Thread(
            target=self._recording_loop,
            name='faster-whisper-asr-worker',
            daemon=True,
        )
        self._worker.start()

    def _read_parameters(self):
        self.model_size = self.get_parameter('model_size').value
        self.device = self.get_parameter('device').value
        self.compute_type = self.get_parameter('compute_type').value
        self.allow_cpu_fallback = bool(
            self.get_parameter('allow_cpu_fallback').value
        )
        self.record_seconds = float(
            self.get_parameter('record_seconds').value
        )
        self.sample_rate = int(self.get_parameter('sample_rate').value)
        self.input_device_index = int(
            self.get_parameter('input_device_index').value
        )
        self.language = str(self.get_parameter('language').value).strip()
        self.beam_size = int(self.get_parameter('beam_size').value)
        self.min_audio_rms = float(
            self.get_parameter('min_audio_rms').value
        )

        if self.record_seconds <= 0:
            raise ASRStartupError('record_seconds must be greater than zero')
        if self.sample_rate <= 0:
            raise ASRStartupError('sample_rate must be greater than zero')
        if self.beam_size <= 0:
            raise ASRStartupError('beam_size must be greater than zero')
        if self.min_audio_rms < 0:
            raise ASRStartupError('min_audio_rms cannot be negative')

    def _load_dependencies_and_model(self):
        try:
            import pyaudio
        except (ImportError, OSError) as error:
            raise ASRStartupError(
                'PyAudio is unavailable. Install the python3-pyaudio package.'
            ) from error

        try:
            from faster_whisper import WhisperModel
        except (ImportError, OSError) as error:
            raise ASRStartupError(
                'Faster-Whisper is unavailable. Follow RUNNING.md to install '
                'the ASR dependencies for /usr/bin/python3.'
            ) from error

        cuda_device_count = detect_cuda_device_count()
        cuda_compute_types = detect_cuda_compute_types()
        compute_type_text = ', '.join(sorted(cuda_compute_types)) or 'none'
        self.get_logger().info(
            f'CTranslate2 CUDA devices: {cuda_device_count}; '
            f'compute types: {compute_type_text}'
        )

        if cuda_runtime_needs_setup(
            self.device, cuda_device_count, cuda_compute_types
        ):
            raise ASRStartupError(
                'An NVIDIA GPU is visible, but cuBLAS/cuDNN cannot be loaded. '
                'Set LD_LIBRARY_PATH to the pip-installed nvidia/cublas/lib '
                'and nvidia/cudnn/lib directories as shown in RUNNING.md. '
                'CPU fallback is disabled for this configuration error.'
            )

        try:
            primary = resolve_runtime(
                self.model_size,
                self.device,
                self.compute_type,
                cuda_compute_types,
            )
        except ValueError as error:
            raise ASRStartupError(str(error)) from error

        last_error = None
        for choice in fallback_choices(primary, self.allow_cpu_fallback):
            self.get_logger().info(
                'Loading Faster-Whisper: '
                f'model={choice.model_size}, device={choice.device}, '
                f'compute_type={choice.compute_type}'
            )
            try:
                self._model = WhisperModel(
                    choice.model_size,
                    device=choice.device,
                    compute_type=choice.compute_type,
                )
                self._runtime = choice
                break
            except Exception as error:  # Model/runtime errors vary by backend.
                last_error = error
                self.get_logger().warning(
                    'Could not load Faster-Whisper with '
                    f'{choice}: {type(error).__name__}: {error}'
                )

        if self._model is None:
            raise ASRStartupError(
                'No Faster-Whisper runtime could be loaded. Last error: '
                f'{type(last_error).__name__}: {last_error}'
            )

        self._pyaudio = pyaudio
        self._audio = pyaudio.PyAudio()

    def _selected_device_index(self):
        return None if self.input_device_index < 0 else self.input_device_index

    def _validate_microphone(self):
        try:
            if self.input_device_index < 0:
                device = self._audio.get_default_input_device_info()
            else:
                device = self._audio.get_device_info_by_index(
                    self.input_device_index
                )
            if int(device.get('maxInputChannels', 0)) < 1:
                raise ASRStartupError(
                    'Audio device has no input channel: '
                    f'{self.input_device_index}'
                )
            self.get_logger().info(
                'Microphone selected: '
                f'index={int(device["index"])}, name={device["name"]}'
            )
        except ASRStartupError:
            raise
        except Exception as error:
            available = self._input_device_summary()
            raise ASRStartupError(
                f'No usable microphone is available: {error}. '
                f'Input devices: {available}'
            ) from error

    def _input_device_summary(self):
        devices = []
        for index in range(self._audio.get_device_count()):
            info = self._audio.get_device_info_by_index(index)
            if int(info.get('maxInputChannels', 0)) > 0:
                devices.append(f'{index}:{info.get("name", "unknown")}')
        return ', '.join(devices) if devices else 'none'

    def _record_once(self):
        frames_per_buffer = 1024
        frame_count = int(
            self.sample_rate * self.record_seconds / frames_per_buffer
        )
        stream = self._audio.open(
            format=self._pyaudio.paInt16,
            channels=1,
            rate=self.sample_rate,
            input=True,
            input_device_index=self._selected_device_index(),
            frames_per_buffer=frames_per_buffer,
        )
        frames = []
        try:
            for _ in range(frame_count):
                if self._stop_event.is_set():
                    break
                frames.append(
                    stream.read(frames_per_buffer, exception_on_overflow=False)
                )
        finally:
            stream.stop_stream()
            stream.close()
        return pcm16_to_float32(b''.join(frames))

    def _recording_loop(self):
        while rclpy.ok() and not self._stop_event.is_set():
            self.get_logger().info(
                f'Listening for {self.record_seconds:.1f} seconds...'
            )
            try:
                samples = self._record_once()
            except Exception as error:
                self.get_logger().error(
                    'Microphone recording failed; stopping ASR worker: '
                    f'{type(error).__name__}: {error}'
                )
                return

            if self._stop_event.is_set():
                return

            rms = audio_rms(samples)
            if rms < self.min_audio_rms:
                self.get_logger().info(
                    f'Audio below RMS threshold ({rms:.4f}); not transcribing.'
                )
                continue

            self.get_logger().info(
                'Transcribing audio: '
                f'{len(samples) / self.sample_rate:.1f}s'
            )
            try:
                segments, info = self._model.transcribe(
                    samples,
                    language=self.language or None,
                    beam_size=self.beam_size,
                    word_timestamps=False,
                    condition_on_previous_text=False,
                    vad_filter=False,
                )
                text = join_segments(segments)
            except Exception as error:
                self.get_logger().error(
                    'Faster-Whisper transcription failed: '
                    f'{type(error).__name__}: {error}'
                )
                continue

            if not text:
                self.get_logger().info('No speech was recognized.')
                continue

            message = String()
            message.data = text
            self.publisher.publish(message)
            language = getattr(info, 'language', self.language or 'unknown')
            self.get_logger().info(
                f'Published final transcript ({language}): {text}'
            )

    def destroy_node(self):
        """Stop the worker and release microphone resources."""
        self._stop_event.set()
        if self._worker is not None and self._worker.is_alive():
            self._worker.join(timeout=self.record_seconds + 1.0)
        if self._audio is not None:
            self._audio.terminate()
            self._audio = None
        return super().destroy_node()


def main(args=None):
    """Run the Faster-Whisper ROS node."""
    rclpy.init(args=args)
    node = None
    try:
        node = FasterWhisperASRNode()
        rclpy.spin(node)
    except ASRStartupError as error:
        if node is not None:
            node.get_logger().error(f'ASR startup failed: {error}')
        else:
            print(f'ASR startup failed: {error}')
    except KeyboardInterrupt:
        pass
    finally:
        if node is not None:
            node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
