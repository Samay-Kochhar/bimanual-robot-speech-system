# Running the Phase 1 ROS 2 Speech Skeleton

This phase uses manual text in place of real ASR. Rasa remains a separate HTTP
NLU service. TTS and HSM are mock ROS nodes that log what they receive.

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
colcon build --packages-select asr_node nlu_node tts_node
source install/setup.bash
```

Use the ROS 2 distribution installed on the machine if it is not Jazzy.

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
colcon build --packages-select nlu_node
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
colcon build --packages-select tts_node
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
