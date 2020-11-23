# Last changed May 31st, 2017
# Thresholds set at (4,2) within MPR121_edited.py
# Always run this script with <sudo>, otherwise you won't get access to the MPR121
# Also use python 3, otherwise the datetime.timestamp and datetime.fromtimestamp methods won't work

"""This function prints the ‘raw’ ADC values for all 12 electrodes from a single sensor.
Normal untouched ADC values should range between 215-230, whereas they should decrease
to about 50-90 when touched. Different sensors addresses can be selected by adding the
-a or –-address option followed by either one of the following addresses:
0x5A, 0x5B, 0x5C, 0x5D (for sensors 1-4, respectively).
ata can be saved to a .txt file through the -s or –-save option.
"""

import sys, time, argparse
from datetime import datetime
import Adafruit_MPR121.MPR121_edited as MPR121

# Set up argparse
parser = argparse.ArgumentParser()
parser.add_argument('-s', '--save', help = 'save raw ADC values to a .txt file',
action = "store_true")
parser.add_argument('-a', '--address', help = 'specify MPR121 address (values: \
0x5A (default), 0x5B, 0x5C, 0x5D)', type = str)
args = parser.parse_args()

if args.address == None or args.address == '0x5A':
    address = 0x5A
elif args.address == '0x5B':
    address = 0x5B
elif args.address == '0x5C':
    address = 0x5C
elif args.address == '0x5D':
    address = 0x5D    
elif not args.address in ['0x5A', '0x5B', '0x5C', '0x5D']:
    print('Error: invalid address specified (must be 0x5A, 0x5B, 0x5C, or 0x5D).')
    sys.exit(1)

# Create MPR121 instance.
cap = MPR121.MPR121()

# Start communication with the MPR121 chip.
if not cap.begin(address=address):
    print('Error initializing MPR121. Check your wiring!')
    sys.exit(1)

if args.save:
    # Ask user for mouse ID and trial number to create corresponding text file.
    filename = input('Filename: ')
    if filename[-4:] != '.txt':
        filename += '.txt'

# Main loop to print a message every time a pin is touched.
# Note: this takes about 20 ms per loop iteration!
print('Collecting data. Press Ctrl-C to quit.')
while True:
    touch_status = cap.touched()

    filtered = [cap.filtered_data(i) for i in range(12)]

    # Print touch status and raw data:
    print('Touch status: {}, Filtered: {}'.format(str(touch_status).zfill(4),filtered), end=12*' ', flush=True)
    print('\r', end='', flush=True)

    if args.save:
        with open(filename, a) as f:
            f.write('{}, {}, {}\n'.format(datetime.now().timestamp(),touch_status.zfill(4),filtered.strip('[]'))) # Need to convert touch_status and filtered to strings?
