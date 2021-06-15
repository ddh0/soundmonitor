# Python 3.8.2
# Started on 2020-05-14 by Dylan Halladay

""" Program to monitor audio input levels
    and react to noises in realtime.
    
                PLEASE READ
    
    This program prioritizes reaction time over
    efficient RAM/CPU usage. As such, several
    single-task child processes will be spawned
    upon execution, each with only one job.
    
    This allows for realtime response to noises
    based on their loudness.
    
                SETTINGS
    
    To change mono/stereo, sampling rate, and
    record time, change the constants in the 
    settings section of the file.
    
    The program only accepts 16-bit audio. """

import sys
import pyaudio # I had to use "python -m pipwin install pyaudio" on Windows (version 0.2.11)
import audioop
import queue # Just for exceptions from mp.Queue()
import datetime
import time
import numpy as np # pip install numpy
import multiprocessing as mp
from decimal import Decimal, InvalidOperation

# ========================
# Settings
# ========================

# Mono or stereo mic?
CHANNELS = 1

# Sampling rate of mic in Hz?
RATE = 48000

# RMS quantize level (output precision)
RMS_rounder = Decimal('1')

# dB quantize level (output precision)
dB_rounder = Decimal('01.23')

# Output prefix enabled? True/False
# Content of prefix is determined in prefix() function
enable_prefixes = True

# Desired record time per output in seconds?
# Higher = Less output/sec, may be more accurate, may miss very fast sounds
# Lower = More output/sec, may be less accurate, catches very fast sounds
# (Time required to process sound may make time between outputs vary slightly)
record_time = 0.1

# ========================
# End of settings
# ========================

class Sound(object):
    """ Used to give detected sounds a dB value and loudness rating.
        
        Raw attributes are type Decimal, others are type string.
        
        Non-raw attributes are truncated according to settings. """
    
    def __init__(self):
        self.visual_string = "Not set" # string
        self.raw_RMS = "Not set" # Decimal
        self.raw_dB = "Not set" # Decimal
        self.RMS = "Not set" # string
        self.dB = "Not set" # string

# ========================
# Basic functions
# ========================

def queue_put(queue_name, given):
    """ I put the try/except in a function to avoid
        typing it several times. """
    
    try:
        queue_name.put(given)

    except queue.Empty:
        print("queue_put: Queue empty!")

    except queue.Full:
        print("queue_put: Queue full!")

def queue_get(queue_name):
    """ I put the try/except in a function to avoid
        typing it several times. """
    
    try:
        x = queue_name.get()

    except queue.Empty:
        print("queue_get: Queue empty!")
        return None

    except queue.Full:
        print("queue_get: Queue full!")
        return None
    
    return x

def prefix():
    """ Only retuns string if prefixes are enabled in settings """

    if enable_prefixes:
        # Return timestamp in "2020-05-15 HH:MM:SS.xx" format

        date_now = datetime.datetime.today().strftime('%Y-%m-%d') # YYYY-MM-DD
        time_now = datetime.datetime.today().strftime('%H:%M:%S.%f')[:-4] # HH:MM:SS.xxxxxx --> HH:MM:SS.xx

        return date_now + " " + time_now + " - "

    else:
        return ""
    

# Audio Monitor Process --> Measure Sound Process --> Rate Sound Process --> Sound Handler Process

# ========================
# Audio Monitor Process
# ========================

def AudioMonitorProcess(MeasureSoundQueue):
    """ Watch audio stream, get chunk.
        
        ('chunk' means a group of individual audio samples/frames)
        
        Put chunk in MeasureSoundQueue. """
    
    # Calculate chunk length based on settings
    CHUNK_LENGTH = int(RATE * record_time)
    
    # Open audio input stream with PyAudio
    
    print("Opening audio stream...")
    
    audio = pyaudio.PyAudio()
    stream = audio.open(format=pyaudio.paInt16, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=CHUNK_LENGTH)
    
    # Capture stream

    # docs: read(num_frames, exception_on_overflow=True)

    while True:
        # Add try/except here!
        queue_put(MeasureSoundQueue, stream.read(CHUNK_LENGTH, exception_on_overflow=True))

# ========================
# Measure Sound Process
# ========================

# Store .attributes as strings!

def MeasureSoundProcess(MeasureSoundQueue, RateSoundQueue):
    """ Get RMS of chunk, convert RMS to dB.
    
        Create Sound object with .dB and .RMS.
        
        Put Sound object in RateSoundQueue. """
        
    y = Sound()
    y.visual_string = ""
    while True:
        x = Sound()
        a = queue_get(MeasureSoundQueue)

        if x != y:
            x.raw_RMS = Decimal(audioop.rms(a, 2)) # 2 refers to bit depth of audio stream IN BYTES
            x.raw_dB = Decimal('20') * x.raw_RMS.log10()
            
            # How many bars to display?
            
            try:
                visuals_count = (x.raw_dB * Decimal('0.1'))**Decimal('2')
                x.visual_string = "|" * int(visuals_count)
            
            except (InvalidOperation, OverflowError) as e:
                x.visual_string = y.visual_string
            
            # See class Sound() for info on attrs
            
            skip = False
            
            try:
                x.RMS = str(x.raw_RMS.quantize(RMS_rounder)).zfill(5)
                x.dB = str(x.raw_dB.quantize(dB_rounder)).zfill(4)

            except InvalidOperation:
                skip = True
            
            if not skip: queue_put(RateSoundQueue, x)
            
            y = x

# ========================
# Rate Sound Process
# ========================

def RateSoundProcess(RateSoundQueue, ZeroQueue, AmbientQueue, QuietQueue, ModerateQueue, LoudQueue, ExtremeQueue):
    """ Take Sound object from RateSoundQueue.
    
        Assign Sound object to queue based on rating:

            [zero, ambient, quiet, moderate, loud, extreme]
        
        Put object in correct queue based on loudness rating. """
        
    # -Infinity to next are zero
    AmbientLevel = Decimal('0.05') # Here to next are ambient
    QuietLevel = Decimal('30.0') # Here to next are quiet
    ModerateLevel = Decimal('45.0') # Here to next are moderate
    LoudLevel = Decimal('75.0') # Here to next are loud
    ExtremeLevel = Decimal('82.0') # Here and up are extreme
    
    y = None
    while True:
        x = queue_get(RateSoundQueue)
        
        if x != y:
            if x.raw_dB < AmbientLevel: queue_put(ZeroQueue, x)
            if x.raw_dB >= AmbientLevel and x.raw_dB < QuietLevel: queue_put(AmbientQueue, x)
            if x.raw_dB >= QuietLevel and x.raw_dB < ModerateLevel: queue_put(QuietQueue, x)
            if x.raw_dB >= ModerateLevel and x.raw_dB < LoudLevel: queue_put(ModerateQueue, x)
            if x.raw_dB >= LoudLevel and x.raw_dB < ExtremeLevel: queue_put(LoudQueue, x)
            if x.raw_dB >= ExtremeLevel: queue_put(ExtremeQueue, x)
            
            y = x
    
# ========================
# Sound Handler Processes
# ========================

def ZeroSoundHandlerProcess(ZeroQueue):
    """ Display text based on recieved Sound object """

    y = Sound() # Dummy Sound object, see bottom of loop
    y.dB = ""

    while True:
        x = queue_get(ZeroQueue)
        if x is not None and x.dB != y.dB:
            # If we got a sound and it's not the same
            # volume as the last sound
            print(prefix() + x.RMS + " RMS - " + x.dB + " dB - Zero     - " + x.visual_string)
            y = x

def AmbientSoundHandlerProcess(AmbientQueue):
    """ Display text based on recieved Sound object """

    y = Sound() # Dummy Sound object, see bottom of loop
    y.dB = ""

    while True:
        x = queue_get(AmbientQueue)
        if x is not None and x.dB != y.dB:
            # If we got a sound and it's not the same
            # volume as the last sound
            print(prefix() + x.RMS + " RMS - " + x.dB + " dB - Ambient  - " + x.visual_string)
            y = x

def QuietSoundHandlerProcess(QuietQueue):
    """ Display text based on recieved Sound object """

    y = Sound() # Dummy Sound object, see bottom of loop
    y.dB = ""

    while True:
        x = queue_get(QuietQueue)
        if x is not None and x.dB != y.dB:
            # If we got a sound and it's not the same
            # volume as the last sound
            print(prefix() + x.RMS + " RMS - " + x.dB + " dB - Quiet    - " + x.visual_string)
            y = x

def ModerateSoundHandlerProcess(ModerateQueue):
    """ Display text based on recieved Sound object """

    y = Sound() # Dummy Sound object, see bottom of loop
    y.dB = ""

    while True:
        x = queue_get(ModerateQueue)
        if x is not None and x.dB != y.dB:
            # If we got a sound and it's not the same
            # volume as the last sound
            print(prefix() + x.RMS + " RMS - " + x.dB + " dB - Moderate - " + x.visual_string)
            y = x

def LoudSoundHandlerProcess(LoudQueue):
    """ Display text based on recieved Sound object """

    y = Sound() # Dummy Sound object, see bottom of loop
    y.dB = ""

    while True:
        x = queue_get(LoudQueue)
        if x is not None and x.dB != y.dB:
            # If we got a sound and it's not the same
            # volume as the last sound
            print(prefix() + x.RMS + " RMS - " + x.dB + " dB - Loud     - " + x.visual_string)
            y = x

def ExtremeSoundHandlerProcess(ExtremeQueue):
    """ Display text based on recieved Sound object """

    y = Sound() # Dummy Sound object, see bottom of loop
    y.dB = ""

    while True:
        x = queue_get(ExtremeQueue)
        if x is not None and x.dB != y.dB:
            # If we got a sound and it's not the same
            # volume as the last sound
            print(prefix() + x.RMS + " RMS - " + x.dB + " dB - Extreme  - " + x.visual_string)
            y = x

# Audio Monitor Process --> Measure Sound Process --> Rate Sound Process --> Sound Handler Process

def main():

    print("Please read my docs! :)")

    # Create Queues
    
    print("Creating queues...")
    
    MeasureSoundQueue = mp.Queue()
    RateSoundQueue = mp.Queue()
    
    ZeroQueue = mp.Queue()
    AmbientQueue = mp.Queue()
    QuietQueue = mp.Queue()
    ModerateQueue = mp.Queue()
    LoudQueue = mp.Queue()
    ExtremeQueue = mp.Queue()

    # Create process objects
    
    print("Creating process objects...")

    AudioMonitorProcessObj = mp.Process(target=AudioMonitorProcess, args=(MeasureSoundQueue,), name="Audio Monitor Process")
    
    MeasureSoundProcessObj = mp.Process(target=MeasureSoundProcess, args=(MeasureSoundQueue, RateSoundQueue,), name="Measure Sound Process")
    RateSoundProcessObj = mp.Process(target=RateSoundProcess, args=(RateSoundQueue, ZeroQueue, AmbientQueue, QuietQueue, ModerateQueue, LoudQueue, ExtremeQueue), name="Rate Sound Process")
    
    ZeroSoundHandlerProcessObj = mp.Process(target=ZeroSoundHandlerProcess, args=(ZeroQueue,), name="Zero Sound Handler Process")
    AmbientSoundHandlerProcessObj = mp.Process(target=AmbientSoundHandlerProcess, args=(AmbientQueue,), name="Ambient Sound Handler Process")
    QuietSoundHandlerProcessObj = mp.Process(target=QuietSoundHandlerProcess, args=(QuietQueue,), name="Quiet Sound Handler Process")
    ModerateSoundHandlerProcessObj = mp.Process(target=ModerateSoundHandlerProcess, args=(ModerateQueue,), name="Moderate Sound Handler Process")
    LoudSoundHandlerProcessObj = mp.Process(target=LoudSoundHandlerProcess, args=(LoudQueue,), name="Loud Sound Handler Process")
    ExtremeSoundHandlerProcessObj = mp.Process(target=ExtremeSoundHandlerProcess, args=(ExtremeQueue,), name="Extreme Sound Handler Process")
    
    # Start processes in order
    
    print("Starting processes...")
    
    AudioMonitorProcessObj.start()
    
    MeasureSoundProcessObj.start()
    RateSoundProcessObj.start()
    
    ZeroSoundHandlerProcessObj.start()
    AmbientSoundHandlerProcessObj.start()
    QuietSoundHandlerProcessObj.start()
    ModerateSoundHandlerProcessObj.start()
    LoudSoundHandlerProcessObj.start()
    ExtremeSoundHandlerProcessObj.start()

if __name__ == '__main__':
    main()