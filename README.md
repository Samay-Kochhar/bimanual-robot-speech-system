# Bimanual Robot Speech System

This project implements a **modular speech pipeline** for a bimanual robot setup.  
The goal is to allow a human operator to speak natural commands

### ✔ Current Status (Work in Progress)

- **ASR (speech-to-text)**: Working  
  - Using *Faster-Whisper (tiny, CPU)*  
  - Low-latency voice transcription  
  - Robust to natural sentence variations  

- **NLU (understanding)**: Working  
  - Powered by Rasa  
  - Intents implemented: `put`, `give`, `describe_object`, `stop`, `greet`, `affirm`, `deny`  
  - Entities extracted: `object`, `color`, `relation`, `elongated`, etc.  
  - Based on professor-provided JSGF command set

- **Pipeline Integration**: Working  
  - Speech → ASR → Rasa → text summary  
  - Runs fully on macOS M1  
  - Modular design (ready for ROS integration later)

- **TTS (text-to-speech)**: Temporary  
  - Using macOS `say` command  
  - Will be replaced with neural TTS later

### 🔧 How to Run (short version)

1. Start Rasa:
   rasa train
   rasa run --enable-api --port 5005
2. Run python file
   python asr_rasa_loop.py
3. Speak command:
   eg.  "put the yellow cylinder in the box"
    - "give me the red cube"
    - "describe the long yellow object near the blue box"
    - "stop"
  
