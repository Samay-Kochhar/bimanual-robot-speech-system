# Bimanual Robot Speech System

This project is a ROS 2 speech-command pipeline for a bimanual robot. A user can
speak or type a command such as "put the red apple into the blue bowl". The
system turns that command into structured XML and sends it to a mock robot HSM
interface.

The real robot HSM is not connected yet. The current HSM transport is mocked for
safe testing and demos.

## What works now

- ROS 2 Jazzy modular pipeline.
- Faster-Whisper microphone ASR on the lab GTX 1060 using CUDA,
  `model_size=medium`, and `compute_type=int8_float32`.
- Manual ASR fallback for typed test commands.
- Push-to-talk ASR mode for demos.
- Rasa HTTP NLU parsing through `http://localhost:5005/model/parse`.
- Supported robot commands: `put`, `give`, and `stop`.
- XML generation for executable commands.
- Mock HSM ROS 2 action transport.
- Modular TTS node; demo launch uses print-mode TTS.
- Live-tested relations: `in`, `on`, `left`, `right`, `front`, `behind`.
- Placeholder `pointingTime="1"` for `this` and `that`.
- Selected ROS tests: 70 tests, 0 errors, 0 failures, 3 skipped.

## Quick Start

Use separate terminals. Rasa runs in its conda environment; ROS runs with system
Python 3.12.

### Terminal 1: start Rasa

```bash
conda activate rasa
cd /techfak/user/skochhar/bimanual-robot-speech-system/rasa
rasa run --enable-api --port 5005
```

Leave this terminal running.

### Terminal 2: build and launch ROS action demo

```bash
cd /techfak/user/skochhar/bimanual-robot-speech-system/ros2_ws
source /opt/ros/jazzy/setup.bash
colcon build --packages-select \
  asr_node hsm_interfaces nlu_node speech_bringup tts_node \
  --cmake-args -DPython3_EXECUTABLE=/usr/bin/python3
source install/setup.bash
ros2 launch speech_bringup action_demo.launch.py
```

This starts:

- `nlu_node`
- `tts_node` in print mode
- `mock_hsm_action`

### Terminal 3: send manual ASR commands

```bash
source /opt/ros/jazzy/setup.bash
source /techfak/user/skochhar/bimanual-robot-speech-system/ros2_ws/install/setup.bash
ros2 run asr_node manual_asr "put the red apple into the blue bowl"
```

More test commands:

```bash
ros2 run asr_node manual_asr "give me the red apple"
ros2 run asr_node manual_asr "put the red block to the left of the green cube"
ros2 run asr_node manual_asr "put the red apple"
ros2 run asr_node manual_asr "stop"
```

Expected behavior:

- Complete commands produce TTS confirmation and XML sent to the mock HSM action.
- Missing information produces a clarification question and no XML.
- Unsupported commands produce a fallback response and no XML.

### Optional Terminal 4: GPU push-to-talk ASR

Run this instead of manual ASR when the microphone and CUDA environment are ready:

```bash
export LD_LIBRARY_PATH="$HOME/.local/lib/python3.12/site-packages/nvidia/cublas/lib:$HOME/.local/lib/python3.12/site-packages/nvidia/cudnn/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
source /opt/ros/jazzy/setup.bash
source /techfak/user/skochhar/bimanual-robot-speech-system/ros2_ws/install/setup.bash
ros2 run asr_node faster_whisper_asr --ros-args \
  -p mode:=push_to_talk \
  -p model_size:=medium \
  -p device:=cuda \
  -p compute_type:=int8_float32
```

Press Enter to start recording, speak one command, then press Enter again to
stop and transcribe. The node publishes one final transcript to
`/asr/transcript` and waits for the next command.

For CUDA troubleshooting and dependency setup, see [RUNNING.md](RUNNING.md).

## Architecture

```text
microphone -> faster_whisper_asr --+
                                   |
typed text -> manual_asr ----------+--> /asr/transcript
                                        |
                                        v
                                     nlu_node ---- HTTP ----> Rasa
                                        |
                    +-------------------+-------------------+
                    |                                       |
                    v                                       v
                /tts/speak                           XML user_task
                    |                                       |
                    v                                       v
                 tts_node                 /hsm/execute_user_task action
                                                      |
                                                      v
                                               mock_hsm_action
```

## Supported commands

### Put

Examples:

```text
put the red apple into the blue bowl
put the long red apple into the small blue bowl
put the green block on the yellow box
put the red block to the left of the green cube
put the red block in front of the green cube
put this object in the box
```

Supported relations:

```text
in, on, left, right, front, behind
```

### Give

Examples:

```text
give me the red apple
give one blue block
give me this object
give me that long tube
```

### Stop

Examples:

```text
stop
halt
abort
cancel that
```

## XML example

Input:

```text
put the red apple into the blue bowl
```

Generated XML shape:

```xml
<?xml version="1.0" encoding="UTF-8" standalone="no" ?>
<user_task type="put" armPref="">
  <object>
    <resolve_request count="the" class="apple" color="red" elongated="" pointingTime="0" size="" xpos="" ypos="" />
  </object>
  <target relation="in">
    <resolve_request count="the" class="bowl" color="blue" elongated="" pointingTime="0" size="" xpos="" ypos="" />
  </target>
  <STATUS origin="Submitter" value="initiated" />
</user_task>
```

For commands using `this` or `that`, `pointingTime` is currently a placeholder:

```text
pointingTime="1"
```

Real pointing timestamps are future work.

## Main ROS interfaces

| Interface | Type | Purpose |
|---|---|---|
| `/asr/transcript` | `std_msgs/msg/String` | Final ASR text into NLU. |
| `/tts/speak` | `std_msgs/msg/String` | Text that should be spoken or printed. |
| `/hsm/execute_user_task` | `hsm_interfaces/action/ExecuteUserTask` | Mock HSM action receiving XML goals. |
| `/hsm/xml` | `std_msgs/msg/String` | Compatibility topic mode for XML. |

## Run tests

```bash
cd /techfak/user/skochhar/bimanual-robot-speech-system/ros2_ws
source /opt/ros/jazzy/setup.bash
source install/setup.bash
colcon test --packages-select \
  asr_node hsm_interfaces nlu_node speech_bringup tts_node \
  --event-handlers console_direct+
colcon test-result --verbose
```

Current selected result:

```text
70 tests, 0 errors, 0 failures, 3 skipped
```

## Current limitations

- The real robot HSM is not connected; HSM behavior is mocked.
- `pointingTime` for `this` and `that` is a placeholder.
- ASR publishes final transcripts only; no partial transcript messages yet.
- Voice activity detection is not implemented yet.
- ROS speech topics currently use `std_msgs/msg/String`.
- Rasa training data is still small and should be expanded with more real speech
  examples.
- Plural object normalization is not implemented.

## More documentation

- [RUNNING.md](RUNNING.md): detailed setup, CUDA, ASR, build, and troubleshooting.
- [DEMO.md](DEMO.md): short demo sequence for presentation.
- [PROGRESS.md](PROGRESS.md): implementation history and current status.
