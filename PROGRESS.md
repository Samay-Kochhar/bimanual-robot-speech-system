# Project Progress

## Completed today

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

## Current architecture

```text
manual_asr -> /asr/transcript -> nlu_node -> Rasa /model/parse
                                      |-> /tts/speak -> tts_node
                                      `-> /hsm/xml   -> mock_hsm
```

All ROS topic payloads currently use `std_msgs/msg/String`.

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
colcon build --packages-select asr_node nlu_node tts_node
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

### Manual ASR tests

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
colcon test --packages-select nlu_node --event-handlers console_direct+
colcon test-result --verbose
```

## Current limitations

- ASR is manual; no microphone or speech recognition is connected.
- TTS only logs text and does not synthesize audio.
- HSM is a logging mock; no robot action is executed.
- Clarification is single-turn and does not retain dialogue state.
- `this` and `that` use `pointingTime="1"` until real pointing timestamps exist.
- Rasa training data is still small and should be expanded using professor
  grammar examples and real ASR transcripts.

## Recommended next phases

1. **Phase 3: modular TTS backend** — keep `/tts/speak`, add a replaceable audio
   backend and retain the logging backend for tests.
2. **Phase 4: HSM action interface** — replace or complement `/hsm/xml` with a
   ROS 2 action client, including execution feedback, cancellation, and errors.
3. **Phase 5: real ASR integration** — replace `manual_asr` with the team ASR
   node while preserving the `/asr/transcript` interface.
