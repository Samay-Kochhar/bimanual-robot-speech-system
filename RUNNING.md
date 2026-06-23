# Running the ROS 2 Speech System

The ROS 2 Jazzy system accepts microphone input through Faster-Whisper or typed
input through `manual_asr`. Rasa remains a separate HTTP NLU service. TTS is
modular, and the HSM uses either the compatibility topic or mock action.

## 1. Start Rasa

Open a terminal and activate the existing Rasa Pro environment:

```bash
conda activate rasa
cd /techfak/user/skochhar/bimanual-robot-speech-system/rasa
rasa run --enable-api --port 5005
```

The ROS NLU node expects:

```text
http://localhost:5005/model/parse
```

## 2. Build the ROS workspace

Open another terminal:

```bash
cd /techfak/user/skochhar/bimanual-robot-speech-system/ros2_ws
source /opt/ros/jazzy/setup.bash
colcon build --packages-select \
  asr_node hsm_interfaces nlu_node speech_bringup tts_node \
  --cmake-args -DPython3_EXECUTABLE=/usr/bin/python3
source install/setup.bash
```

This project is currently tested with ROS 2 Jazzy. Keep the explicit system
Python argument, especially when a conda environment is active.

## 3. Start the ROS nodes

Run each command in a separate terminal. In every terminal, source ROS and the
workspace first:

```bash
source /opt/ros/jazzy/setup.bash
source /techfak/user/skochhar/bimanual-robot-speech-system/ros2_ws/install/setup.bash
```

Start the NLU/Rasa bridge:

```bash
ros2 run nlu_node nlu_node
```

Start the mock TTS output:

```bash
ros2 run tts_node tts_node
```

Start the mock HSM XML receiver:

```bash
ros2 run nlu_node mock_hsm
```

## 4. Publish a manual transcript

For an interactive prompt:

```bash
ros2 run asr_node manual_asr
```

Enter one command per line, for example:

```text
put the red block on the green cube
give me the blue cylinder
stop
```

For a single command:

```bash
ros2 run asr_node manual_asr "put the red block on the green cube"
```

The standard ROS CLI can also be used without the manual publisher node:

```bash
ros2 topic pub --once /asr/transcript std_msgs/msg/String \
  "{data: 'give me the blue cube'}"
```

## Expected result

For an executable `put` or `give` command:

1. The NLU node logs the transcript and Rasa result.
2. The TTS node logs a line beginning with `TTS OUTPUT:`.
3. The mock HSM node logs the generated XML.

For an incomplete or unsupported command, the TTS node logs a clarification or
error response and no XML is published.

## Optional Rasa URL override

The default endpoint can be changed without editing source:

```bash
ros2 run nlu_node nlu_node --ros-args \
  -p rasa_url:=http://localhost:5005/model/parse
```

## Phase 2 commands

After changing Rasa training data, retrain from the existing Rasa environment:

```bash
conda activate rasa
cd /techfak/user/skochhar/bimanual-robot-speech-system/rasa
rasa data validate
rasa train nlu
rasa run --enable-api --port 5005
```

Build and run the focused ROS NLU tests:

```bash
cd /techfak/user/skochhar/bimanual-robot-speech-system/ros2_ws
source /opt/ros/jazzy/setup.bash
colcon build --packages-select hsm_interfaces nlu_node \
  --cmake-args -DPython3_EXECUTABLE=/usr/bin/python3
source install/setup.bash
pytest -q \
  src/nlu_node/test/test_command_logic.py \
  src/nlu_node/test/test_xml_builder.py
```

Example Phase 2 transcripts:

```bash
ros2 run asr_node manual_asr "put the red apple in the blue bowl"
ros2 run asr_node manual_asr "put one green block on the table"
ros2 run asr_node manual_asr "put this object in the box"
ros2 run asr_node manual_asr "give me the red apple"
ros2 run asr_node manual_asr "give one blue block"
ros2 run asr_node manual_asr "stop"
```

The confidence threshold defaults to `0.60` and can be overridden with
`-p min_intent_confidence:=0.70` when starting `nlu_node`.

## Phase 3: modular TTS

The ROS interface remains `/tts/speak`. The backend is selected inside
`tts_node`, so the NLU node does not depend on a speech engine.

Backend modes:

- `auto` (default): use the first installed command from `spd-say`,
  `espeak-ng`, `espeak`, or macOS `say`; otherwise print.
- `print`: always log the utterance without audio.
- `command`: use the executable named by the `command` parameter, or fall back
  to print when it is unavailable.
- `kokoro`: currently documents the extension point and falls back to print;
  Kokoro is not installed or required.

Build and test:

```bash
cd /techfak/user/skochhar/bimanual-robot-speech-system/ros2_ws
source /opt/ros/jazzy/setup.bash
colcon build --packages-select tts_node \
  --cmake-args -DPython3_EXECUTABLE=/usr/bin/python3
source install/setup.bash
colcon test --packages-select tts_node --event-handlers console_direct+
colcon test-result --verbose
```

Run with automatic command discovery:

```bash
ros2 run tts_node tts_node
```

Force deterministic print mode:

```bash
ros2 run tts_node tts_node --ros-args -p backend:=print
```

Request a specific installed command:

```bash
ros2 run tts_node tts_node --ros-args \
  -p backend:=command -p command:=spd-say
```

Publish a direct TTS test from another sourced ROS terminal:

```bash
ros2 topic pub --once /tts/speak std_msgs/msg/String \
  "{data: 'Phase three text to speech test'}"
```

A future `KokoroTTSBackend` can implement the interface in `backends.py` and be
returned by `select_backend()` without changing `/tts/speak` or the NLU node.

## Phase 4: HSM topic and action modes

The default remains topic mode for compatibility. Action mode uses the
`hsm_interfaces/action/ExecuteUserTask` action on
`/hsm/execute_user_task`.

Build the interface and dependent nodes:

```bash
cd /techfak/user/skochhar/bimanual-robot-speech-system/ros2_ws
source /opt/ros/jazzy/setup.bash
colcon build --packages-select hsm_interfaces nlu_node \
  --cmake-args -DPython3_EXECUTABLE=/usr/bin/python3
source install/setup.bash
```

Run tests:

```bash
colcon test --packages-select hsm_interfaces nlu_node \
  --event-handlers console_direct+
colcon test-result --verbose
```

### Topic mode (default)

Run in separate sourced terminals:

```bash
ros2 run nlu_node mock_hsm
ros2 run nlu_node nlu_node
```

The NLU node publishes executable XML to `/hsm/xml`.

### Action mode

Start the mock action server:

```bash
ros2 run nlu_node mock_hsm_action
```

Start the NLU node in action mode:

```bash
ros2 run nlu_node nlu_node --ros-args -p hsm_mode:=action
```

Start TTS in another terminal, then submit a manual transcript:

```bash
ros2 run tts_node tts_node --ros-args -p backend:=print
ros2 run asr_node manual_asr "put the red apple in the blue bowl"
```

If the action server is not running, the NLU node publishes a spoken error on
`/tts/speak` instead of crashing. The server wait defaults to one second and can
be changed with `-p hsm_server_timeout:=2.0`.

Inspect the action directly:

```bash
ros2 action info /hsm/execute_user_task
```

Send a direct test goal:

```bash
ros2 action send_goal /hsm/execute_user_task \
  hsm_interfaces/action/ExecuteUserTask \
  "{xml: '<user_task type=\"stop\"><STATUS origin=\"Submitter\" value=\"initiated\"/></user_task>'}" \
  --feedback
```

## Phase 5: demo launch workflow

Build the complete demonstration stack:

```bash
cd /techfak/user/skochhar/bimanual-robot-speech-system/ros2_ws
source /opt/ros/jazzy/setup.bash
colcon build --packages-select \
  asr_node hsm_interfaces nlu_node speech_bringup tts_node \
  --cmake-args -DPython3_EXECUTABLE=/usr/bin/python3
source install/setup.bash
```

Start Rasa separately in the existing conda environment, then choose one launch
mode.

Topic mode:

```bash
ros2 launch speech_bringup topic_demo.launch.py
```

Action mode:

```bash
ros2 launch speech_bringup action_demo.launch.py
```

Both launch files start `nlu_node`, print-mode `tts_node`, and the matching mock
HSM. Manual ASR remains a separate one-shot command:

```bash
ros2 run asr_node manual_asr "put the red apple in the blue bowl"
```

Optional launch overrides:

```bash
ros2 launch speech_bringup topic_demo.launch.py \
  rasa_url:=http://localhost:5005/model/parse \
  min_intent_confidence:=0.70
```

Test the bringup package:

```bash
colcon test --packages-select speech_bringup --event-handlers console_direct+
colcon test-result --verbose
```

See `DEMO.md` for the short professor demonstration sequence.

## Current integration boundary

Both ASR paths publish final text as `std_msgs/msg/String` on
`/asr/transcript`. Partial and final hypotheses can be represented later with a
custom transcript message; no such custom message is required now.

## Phase 7: Faster-Whisper microphone ASR

The ASR node runs with ROS Jazzy's system Python 3.12, not the Rasa conda
environment. Install its Python dependencies once, without sudo:

```bash
conda deactivate
cd /techfak/user/skochhar/bimanual-robot-speech-system
/usr/bin/python3 -m pip install --user --break-system-packages \
  -r ros2_ws/src/asr_node/requirements-asr.txt
```

This installs Faster-Whisper and user-space CUDA libraries but does not download
a Whisper model. On first startup, `medium` downloads about 1.6 GB; `small`
downloads about 500 MB; `base` downloads about 150 MB.

Expose the pip-installed CUDA libraries in every ASR terminal:

```bash
export LD_LIBRARY_PATH="$HOME/.local/lib/python3.12/site-packages/nvidia/cublas/lib:$HOME/.local/lib/python3.12/site-packages/nvidia/cudnn/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
```

On the lab GTX 1060, CTranslate2 supports `int8_float32` rather than `float16`.
Automatic mode therefore selects `medium`, CUDA, `int8_float32`. If the GPU is
visible but the CUDA libraries are missing from `LD_LIBRARY_PATH`, startup now
fails with a setup error instead of silently choosing CPU. The fallback order
after CUDA is configured is medium CUDA, small CUDA, then small CPU int8.

Check the microphone independently:

```bash
arecord -D default -f S16_LE -r 16000 -c 1 -d 3 /tmp/asr-test.wav
aplay /tmp/asr-test.wav
```

Verify CUDA before downloading a model:

```bash
/usr/bin/python3 -c 'import ctypes, ctranslate2; ctypes.CDLL("libcublas.so.12"); ctypes.CDLL("libcudnn.so.9"); print("GPU count:", ctranslate2.get_cuda_device_count()); print("CUDA compute types:", sorted(ctranslate2.get_supported_compute_types("cuda")))'
```

Expected compute types on the GTX 1060 are `float32`, `int8`, and
`int8_float32`. Then run the real ASR node in a sourced ROS terminal:

```bash
source /opt/ros/jazzy/setup.bash
source /techfak/user/skochhar/bimanual-robot-speech-system/ros2_ws/install/setup.bash
ros2 run asr_node faster_whisper_asr --ros-args \
  -p model_size:=medium \
  -p device:=cuda \
  -p compute_type:=int8_float32
```

The node continuously records 5-second mono windows, ignores very quiet audio,
and publishes each final transcript to `/asr/transcript`. Verify it separately:

```bash
ros2 topic echo /asr/transcript
```

Use the smaller CUDA model if medium latency is too high:

```bash
ros2 run asr_node faster_whisper_asr --ros-args \
  -p model_size:=small
```

Force CPU mode when testing without CUDA:

```bash
ros2 run asr_node faster_whisper_asr --ros-args \
  -p model_size:=small -p device:=cpu -p compute_type:=int8
```

Select a non-default microphone by PyAudio device index:

```bash
/usr/bin/python3 - <<'PY'
import pyaudio
p = pyaudio.PyAudio()
for index in range(p.get_device_count()):
    info = p.get_device_info_by_index(index)
    if info.get('maxInputChannels', 0) > 0:
        print(index, info['name'])
p.terminate()
PY

ros2 run asr_node faster_whisper_asr --ros-args \
  -p input_device_index:=4
```

`manual_asr` remains available and unchanged when microphone capture or model
loading is unavailable.
