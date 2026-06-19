# Professor Demo

The demo uses ROS 2 Jazzy and manual text instead of real ASR. Rasa must be
running before a launch file is started. See `RUNNING.md` for the full manual
node workflow and troubleshooting.

## Preparation

Terminal 1:

```bash
conda activate rasa
cd /techfak/user/skochhar/bimanual-robot-speech-system/rasa
rasa run --enable-api --port 5005
```

Terminal 2:

```bash
cd /techfak/user/skochhar/bimanual-robot-speech-system/ros2_ws
source /opt/ros/jazzy/setup.bash
colcon build --packages-select \
  asr_node hsm_interfaces nlu_node speech_bringup tts_node \
  --cmake-args -DPython3_EXECUTABLE=/usr/bin/python3
source install/setup.bash
```

## Topic-mode demo

Terminal 2:

```bash
ros2 launch speech_bringup topic_demo.launch.py
```

Terminal 3, sourced with ROS and the workspace:

```bash
ros2 run asr_node manual_asr "put the red apple in the blue bowl"
```

Show that the NLU result, TTS text, and XML received by `mock_hsm` all appear in
the launch terminal.

## Action-mode demo

Stop the topic launch with Ctrl-C, then run:

```bash
ros2 launch speech_bringup action_demo.launch.py
```

In Terminal 3:

```bash
ros2 run asr_node manual_asr "give one blue block"
```

Show the action goal, feedback, successful result, and final TTS acknowledgement
in the launch terminal.

## Clarification demo

With either launch mode running:

```bash
ros2 run asr_node manual_asr "put the red apple"
```

Expected result: TTS asks for missing placement information or a target. No XML
or action goal is sent.

## Stop-command demo

```bash
ros2 run asr_node manual_asr "stop"
```

Expected result: a `user_task type="stop"` command reaches the selected mock HSM
transport and TTS confirms the stop request.

## Useful checks

```bash
ros2 node list
ros2 topic list
ros2 action list
```

Topic mode should expose `/hsm/xml`. Action mode should expose
`/hsm/execute_user_task`.

Run the automated ROS checks before the presentation:

```bash
colcon test --packages-select \
  hsm_interfaces nlu_node speech_bringup tts_node \
  --event-handlers console_direct+
colcon test-result --verbose
```

## Troubleshooting

- Confirm Rasa is reachable at `http://localhost:5005/model/parse`.
- Source `/opt/ros/jazzy/setup.bash` and `ros2_ws/install/setup.bash` in every
  ROS terminal.
- If the Rasa conda environment is active while building, keep the explicit
  `-DPython3_EXECUTABLE=/usr/bin/python3` build argument.
- The launch files intentionally use print-mode TTS, so no audio dependency is
  required for the demonstration.
