# Project Progress

## Completed phases

- Completed Phase 1 ROS skeleton with manual ASR, Rasa NLU bridge, mock TTS,
  and mock HSM nodes.
- Completed Phase 2 command interpretation for `put`, `give`, and `stop`.
- Added source/target entity mapping for color, size, elongated shape, position,
  quantifier, relation, and pointing placeholders.
- Added confidence fallback and clarification responses. Invalid or incomplete
  commands do not publish XML.
- Reworked XML generation to produce valid, safely escaped put/give/stop XML.
- Updated and trained Rasa NLU data in the existing Python 3.11 conda
  environment.
- Added command-logic and XML unit tests. The NLU ROS test suite passes.
- Completed Phase 3 modular TTS backend selection while preserving
  `/tts/speak`.
- Added automatic command discovery, explicit command mode, print fallback,
  runtime failure fallback, and backend-selection tests.
- Completed Phase 4 compatibility transport: `/hsm/xml` remains the default,
  and the NLU node can optionally send XML through a ROS 2 action.
- Added `ExecuteUserTask.action`, a mock HSM action server, graceful unavailable
  server handling, action feedback/results, and transport tests.
- Completed Phase 5 demo bringup with separate topic-mode and action-mode ROS 2
  launch files.
- Added a deterministic print-TTS demo stack, launch-structure tests, and a
  professor-facing `DEMO.md` walkthrough.
- Completed Phase 6 documentation cleanup for professor/demo readiness without
  changing runtime behavior.
- Completed Phase 7 fixed-window microphone ASR with Faster-Whisper while
  preserving `manual_asr` as the fallback input path.
- Added automatic CTranslate2 runtime selection, CUDA/CPU fallbacks, clear
  model/device logs, graceful dependency and microphone errors, and
  hardware-independent tests.

## Current architecture

```text
microphone -> faster_whisper_asr --+
                                   |-> /asr/transcript -> nlu_node -> Rasa
typed text -> manual_asr -----------+                      |-> TTS
                                                           `-> HSM topic/action

```

All ROS topic payloads currently use `std_msgs/msg/String`.
`speech_bringup` starts the topic-mode or action-mode demo stack.

## Restart tomorrow

### Terminal 1: Rasa

```bash
conda activate rasa
cd /techfak/user/skochhar/bimanual-robot-speech-system/rasa
rasa run --enable-api --port 5005
```

Retrain first only when Rasa data changes:

```bash
rasa data validate
rasa train nlu
```

### Terminal 2: build ROS

```bash
cd /techfak/user/skochhar/bimanual-robot-speech-system/ros2_ws
source /opt/ros/jazzy/setup.bash
colcon build --packages-select \
  asr_node hsm_interfaces nlu_node speech_bringup tts_node \
  --cmake-args -DPython3_EXECUTABLE=/usr/bin/python3
source install/setup.bash
```

### Terminals 3-5: run nodes

Source this in every ROS terminal:

```bash
source /opt/ros/jazzy/setup.bash
source /techfak/user/skochhar/bimanual-robot-speech-system/ros2_ws/install/setup.bash
```

Then run one command per terminal:

```bash
ros2 run nlu_node nlu_node
ros2 run tts_node tts_node
ros2 run nlu_node mock_hsm
```

TTS defaults to automatic command discovery. For predictable logging-only
behavior:

```bash
ros2 run tts_node tts_node --ros-args -p backend:=print
```

To request an installed command explicitly:

```bash
ros2 run tts_node tts_node --ros-args -p backend:=command -p command:=spd-say
```

HSM topic mode remains the default:

```bash
ros2 run nlu_node mock_hsm
ros2 run nlu_node nlu_node
```

For action mode, replace the topic mock with the action mock and set the NLU
parameter:

```bash
ros2 run nlu_node mock_hsm_action
ros2 run nlu_node nlu_node --ros-args -p hsm_mode:=action
```

### ASR tests

Real microphone ASR uses the system Python user-site dependencies documented in
`RUNNING.md`. Start it separately from the bringup launch:

```bash
ros2 run asr_node faster_whisper_asr
```

The unchanged manual fallback remains available:

Interactive:

```bash
ros2 run asr_node manual_asr
```

One-shot examples:

```bash
ros2 run asr_node manual_asr "put the red apple in the blue bowl"
ros2 run asr_node manual_asr "put this object in the box"
ros2 run asr_node manual_asr "give one blue block"
ros2 run asr_node manual_asr "stop"
```

Run tests:

```bash
cd /techfak/user/skochhar/bimanual-robot-speech-system/ros2_ws
source /opt/ros/jazzy/setup.bash
colcon test --packages-select \
  asr_node hsm_interfaces nlu_node speech_bringup tts_node \
  --event-handlers console_direct+
colcon test-result --verbose
```

## Current limitations

- Microphone ASR uses fixed 5-second windows and publishes final text only.
- Voice activity detection (VAD) is not implemented.
- The GTX 1060 uses CUDA `int8_float32`; it does not expose FP16 through
  CTranslate2.
- TTS audio depends on an installed lightweight command; otherwise it falls
  back to logging.
- Kokoro is not integrated and remains an optional future backend.
- Both HSM transports are mocks; no real robot action is executed.
- Clarification is single-turn and does not retain dialogue state.
- `this` and `that` use `pointingTime="1"` until real pointing timestamps exist.
- Topic payloads use `std_msgs/msg/String`; custom transcript messages can add
  partial/final state and richer metadata later.
- Rasa training data is still small and should be expanded using professor
  grammar examples and real ASR transcripts.

## Next work

1. Add VAD for microphone input and utterance boundaries.
2. Add incremental/streaming transcript feedback if required.
3. Replace the mock action server with the real robot HSM and validate its
   action/XML contract.
4. Replace the placeholder pointing timestamp with real pointing data.
5. Optionally add custom ROS messages/actions for partial transcripts and
   richer execution feedback.
