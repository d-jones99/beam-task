# Last changed May 31st, 2017
# Touch/release thresholds set at (4,2) in MPR121_edited.py
# Always run this script with <sudo> to get access to the MPR121
# Use Python 3 to access datetime.timestamp and datetime.fromtimestamp methods

"""This is the main script that acquires the data during a tapered beam trial.
Add the -c or --camera option to simultaneously record video during the trial.
Data collection can be stopped by pressing Ctrl-C.

N.B.: conversion of video recording to .mp4 requires installation of gpac,
which can be easily done by running <sudo apt-get install gpac> in a command
window.
"""

# Import the necessary modules
import sys, os, time, argparse, atexit
from datetime import datetime
import RPi.GPIO as GPIO
import Adafruit_MPR121.MPR121_edited as MPR121
import picamera

# Set up argparse
parser = argparse.ArgumentParser()
parser.add_argument('-c', '--camera', help = 'enable camera recording',
action = "store_true")
args = parser.parse_args()

# Set the GPIO pin connected to the IRQ pins on the MPR121s
IRQ_PINS = 26

# Create an MPR121 instance for each sensor.
cap1 = MPR121.MPR121()
cap2 = MPR121.MPR121()
cap3 = MPR121.MPR121()
cap4 = MPR121.MPR121()

# Initialize communication with the MPR121s, using different addresses
# for each sensor.
if not (cap1.begin(address=0x5A)
    and cap2.begin(address=0x5B)
    and cap3.begin(address=0x5C)
    and cap4.begin(address=0x5D)
    ):
    print('Error initializing MPR121s. Check your wiring!')
    sys.exit(1)

# Enable the IRQ pins by configuring the GPIO library
GPIO.setmode(GPIO.BCM)
GPIO.setup(26, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.add_event_detect(26, GPIO.FALLING)
atexit.register(GPIO.cleanup)

# Ask user for mouse ID and trial number to create corresponding text file in
# /data/[currentdate]/
while True:
    targetdir = 'data/' + datetime.now().strftime('%Y%m%d')
    os.makedirs(targetdir, mode=0o777, exist_ok=True)
    mouse_id = input('Mouse ID: ')
    trial = input('Trial number: ').zfill(3)
    filename = '{}_{}_raw.txt'.format(mouse_id,trial)

    invalid_chars = ('<>:"/|?*\\')

    # Check for invalid characters in the provided filename
    try:
        for char in invalid_chars:
            if char in filename:
                raise ValueError()
    except ValueError:
        print('Invalid filename, please try again.')
        pass
    else:
        pathname = targetdir + '/' + filename
        break

# Check whether path already exists and ask user how to deal with it
if os.path.isfile(pathname):
    while True:
        appendfile = input('File already exists, do you want to overwite the existing file? [y/n] ').lower()
        if appendfile not in ('y', 'n'):
            print('Invalid answer, please try again.')
        elif appendfile == 'y':
            print('Continuing: ' + pathname + ' will be overwritten.')
            os.remove(pathname)
            break
        elif appendfile == 'n':
            print('Exiting.')
            sys.exit()

# Read touch status to clear any pending interrupts
# (This might not always work the first time, so try 3 times before giving up)
try_clear = 3
while try_clear > 0:
    touch1 = cap1.touched()
    touch2 = cap2.touched()
    touch3 = cap3.touched()
    touch4 = cap4.touched()
    if touch1 + touch2 + touch3 + touch4 == 0:
        input('Press Enter to continue...')
        break
    else:
        time.sleep(1)
        try_clear -= 1
        if try_clear == 0:
            print('One or more electrodes are being touched. Please check the touch sensors and try again.')
            sys.exit(1)

def get_touches():

    # Read touch status from each sensor
    touch1 = cap1.touched()
    touch2 = cap2.touched()
    touch3 = cap3.touched()
    touch4 = cap4.touched()

    # Print touch status from each sensor
    print('cap1: ' + str(touch1).zfill(4)
        + ', cap2: ' + str(touch2).zfill(4)
        + ', cap3: ' + str(touch3).zfill(4)
        + ', cap4: ' + str(touch4).zfill(4)
        )

    # Save touch status from each sensor
    with open(pathname,'a') as f:
        f.write(str(datetime.now().timestamp()) + ',' + str(touch1).zfill(4)
        + ',' + str(touch2).zfill(4)
        + ',' + str(touch3).zfill(4)
        + ',' + str(touch4).zfill(4)
        + '\n')

# Main program
def main():

    # Start video recording if specified by user
    if args.camera:
        global camera
        camera = picamera.PiCamera()
        camera.resolution = (1640,1232)
        time.sleep(0.1)
        camera.start_recording(pathname[:-7] + 'vid.h264', 'h264')
        print("Video recording started.\n")

    print('Collecting data. Press Ctrl-C to quit.')

    # Record the start of data collection
    get_touches()

    # Main loop, waiting for touches (signaled by interrupts) to occur
    while True:
        if GPIO.event_detected(26):
            get_touches()

    # Uncomment the lines below to save the filtered ADC values as well.
    # Note: this will slow down the sampling rate and only supports one MPR121
    # at a time (cap1 by default).
    #    touch_status = cap1.touched()
    #    filtered = [cap1.filtered_data(i) for i in range(12)]
    #    with open(pathname[:-4] + '_full.txt','a') as f:
    #        f.write(str(datetime.now().timestamp()) + ', '
    #        + str(touch_status).zfill(4) + ', ' + str(filtered).strip('[]') + '\n')
    #    print(str(datetime.now().timestamp()).zfill(17) + ', '
    #    + str(touch_status).zfill(4) + ', ' + str(filtered).strip('[]') + '\r')

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('Done collecting data.')

        # If video was recorded, save it to .mp4 format and close the camera
        if args.camera:
            camera.stop_recording()
            conversion_command = 'MP4Box -add ' + pathname[:-7] + 'vid.h264 ' + pathname[:-7] + 'vid.mp4 -quiet'
            os.system(conversion_command)
            print('Video saved.')
            camera.close()
            os.remove(pathname[:-7] + 'vid.h264')
