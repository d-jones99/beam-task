# Last changed May 31st, 2017
# Thresholds set at (4,2) within MPR121_edited.py
# Always run this script with <sudo>, otherwise you won't get access to the MPR121
# Also use python 3 to get access to the datetime.timestamp and datetime.fromtimestamp methods

"""This script can be used to test each of the 48 electrodes once the
tapered beam is constructed. It returns the touch status of each of the
four sensors when a change in touch status is detected. Touch status is
reported in base-two format: 0000 means not touched, 0001 means electrode
0 (2^0), 0002 means electrode 1, 0004 means electrode 2, etc..."""

import sys, os, time, atexit
from datetime import datetime
import RPi.GPIO as GPIO
import Adafruit_MPR121.MPR121_edited as MPR121

# Set the GPIO pin connected to the IRQ pins on the MPR121s
IRQ_PINS = 26

# Create MPR121 instance.
cap1 = MPR121.MPR121()
cap2 = MPR121.MPR121()
cap3 = MPR121.MPR121()
cap4 = MPR121.MPR121()

# Start communication with the MPR121 chips using different addresses for each one.
if not (cap1.begin(address=0x5A)
    and cap2.begin(address=0x5B)
    and cap3.begin(address=0x5C)
    and cap4.begin(address=0x5D)
    ):
    print('Error initializing MPR121s.  Check your wiring!')
    sys.exit(1)

# Enable the IRQ pins by configuring the GPIO library
GPIO.setmode(GPIO.BCM)
GPIO.setup(26, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.add_event_detect(26, GPIO.FALLING)
atexit.register(GPIO.cleanup)

# Read touch status to clear any pending interrupts
cap1.touched()
cap2.touched()
cap3.touched()
cap4.touched()

# Main program
def main():
    print('Collecting data. Press Ctrl-C to quit.')

    # Main loop
    while True:
        if GPIO.event_detected(26):
            touch1 = cap1.touched()
            touch2 = cap2.touched()
            touch3 = cap3.touched()
            touch4 = cap4.touched()
            print('cap1: {}, cap2: {}, cap3: {}, cap4: {}.'.format(touch1, touch2, touch3, touch4))

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('Done collecting data.')
        sys.exit(1)
