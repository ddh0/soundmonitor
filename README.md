# soundmonitor
Standalone python module to visually monitor the ambient sound level in real-time.

# How it works
soundmonitor.py is a Python 3 module that uses the system microphone to measure the loudness of sounds. It does this by manually performing RMS calculations on the raw sample data from the microphone and additionally converting this RMS value to an approximate Decibel value. It then displays a meter that varies in length depending on the calculated loudness of the sound.

The program can be trivially altered to perfer either super frequent display updates or super accurate sound measurements. See the top of the file for instructions.

# Real-time audio processing

The module utilizes 10 separate simultaneous processes to meausure multiple samples at the same time, and in this way the delay between the sound being recorded and displayed is kept extremely short. Even still, this method of processing does not use undue amounts of CPU processing power.

# How to use

Just double click the file to start, but make sure you've changed the settings to match your own system. See inside file for details.
