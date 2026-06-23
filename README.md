# Bimanual Robot Speech System

This repository contains a modular ROS 2 Jazzy speech-command pipeline for a
bimanual robot. It supports microphone transcription with Faster-Whisper or
typed fallback transcripts, while the HSM components remain mocks until the
real robot controller is connected.

## Architecture

```text
microphone -> faster_whisper_asr ----+
                                     |-> /asr/transcript (String)
typed text -> manual_asr ------------+             |
                                                   v
           nlu_node -------- HTTP --------> Rasa /model/parse
              |                                 |
              |<-------- intent/entities -------'
              |
              +----> /tts/speak ----> tts_node ----> print/command backend
              |
              `----> generated XML
                       |---- topic mode:  /hsm/xml ------------> mock_hsm
                       `---- action mode: /hsm/execute_user_task -> mock_hsm_action
```

The `speech_bringup` package provides separate launch files for the complete
topic-mode and action-mode demo stacks.

## Components

- `faster_whisper_asr`: records fixed microphone windows, transcribes them with
  Faster-Whisper, and publishes final text to `/asr/transcript`.
- `manual_asr`: unchanged typed fallback publisher for testing without audio or
  a downloaded ASR model.
- `nlu_node`: the Rasa/XML brain. It calls Rasa at `/model/parse`, validates the
  interpreted command, asks clarification questions when required information
  is missing, generates XML, and selects the configured HSM transport.
- `tts_node`: subscribes to `/tts/speak` and delegates output to a replaceable
  print or command-line TTS backend. Kokoro is an optional future extension.
- `mock_hsm`: compatibility subscriber that receives and logs XML from the
  `/hsm/xml` topic.
- `mock_hsm_action`: mock ROS 2 action server that receives XML goals and
  returns feedback and a success result without controlling a robot.
- `hsm_interfaces`: defines `ExecuteUserTask.action` with an XML goal,
  success/message result, and status feedback.
- `speech_bringup`: starts the NLU, print-mode TTS, and the matching mock HSM
  for topic or action mode.

## HSM transport modes

Topic mode is the default and preserves the existing `/hsm/xml`
`std_msgs/msg/String` interface. Action mode sends the same XML through
`/hsm/execute_user_task` using `hsm_interfaces/action/ExecuteUserTask`.

The mode is controlled by the NLU parameter `hsm_mode`:

```bash
ros2 run nlu_node nlu_node --ros-args -p hsm_mode:=topic
ros2 run nlu_node nlu_node --ros-args -p hsm_mode:=action
```

## Quick demo

Start Rasa in the existing environment:

```bash
conda activate rasa
cd /techfak/user/skochhar/bimanual-robot-speech-system/rasa
rasa run --enable-api --port 5005
```

Build the ROS 2 Jazzy workspace:

```bash
cd /techfak/user/skochhar/bimanual-robot-speech-system/ros2_ws
source /opt/ros/jazzy/setup.bash
colcon build --packages-select \
  asr_node hsm_interfaces nlu_node speech_bringup tts_node \
  --cmake-args -DPython3_EXECUTABLE=/usr/bin/python3
source install/setup.bash
```

Topic mode:

```bash
ros2 launch speech_bringup topic_demo.launch.py
ros2 run asr_node manual_asr "put the red apple in the blue bowl"
```

Action mode:

```bash
ros2 launch speech_bringup action_demo.launch.py
ros2 run asr_node manual_asr "give one blue block"
```

Clarification and stop examples:

```bash
ros2 run asr_node manual_asr "put the red apple"
ros2 run asr_node manual_asr "stop"
```

Run the launch command and each manual-ASR command in separate terminals, with
ROS and the workspace sourced in every ROS terminal. See [DEMO.md](DEMO.md) for
the presentation sequence and [RUNNING.md](RUNNING.md) for complete setup,
testing, and troubleshooting commands.

## ASR integration

The real ASR node and `manual_asr` publish the same `std_msgs/msg/String`
interface, so the NLU, TTS, and HSM components are independent of the input
source. The current microphone node records fixed-duration windows and emits
final transcripts only. A later custom transcript message can distinguish
partial and final hypotheses and carry additional metadata.

## Current limitations

- ASR uses fixed recording windows and final transcripts only.
- Voice activity detection (VAD) is not implemented.
- The first ASR run downloads the selected model; medium is about 1.6 GB and
  small is about 500 MB.
- Both HSM implementations are mocks; no real robot HSM is connected.
- `this` and `that` use a nonzero placeholder `pointingTime` value.
- ROS topic payloads use `std_msgs/msg/String`; richer custom messages can be
  introduced later.
- TTS audio requires a supported local command; print mode always remains
  available.

## Next work

1. Add VAD around microphone capture and final-transcript publication.
2. Add incremental/streaming ASR feedback if required.
3. Connect and validate the real robot HSM action server.
4. Replace the placeholder pointing timestamp with real pointing data.
5. Optionally add custom ROS messages/actions for partial transcripts and richer
   feedback.

Current implementation status is summarized in [PROGRESS.md](PROGRESS.md).
