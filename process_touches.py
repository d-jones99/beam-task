# Last edited June 5th, 2017

"""This script can be used to convert the raw data (stored in the _raw.txt files)
into a more meaningful format. It produces a _touches.txt file for every _raw.txt
file given as input. The _touches.txt file contains start time, duration, and electrode
at which a touch occured.

Some filtering options are available to help clean up the data. By default, the
script will keep a log file with warnings for every touch that has a duration
shorter than 100 ms (as these are usually nose pokes or tail touches rather
than foot faults). The user can revisit these trials using the video data and
confirm that it was indeed a false positive or not. If the threshold option is
used, touches with a duration shorter than the specified duration will be
automatically removed from the _touches.txt files.

In addition, the script deals with two touches that occur shortly (<150 ms) after
each other on adjacent electrodes. This is most likely a paw touching both
electrodes at the same time and should therefore count as 1 foot fault, not 2.
The touch closer to the finish of the beam is deleted in this case.

If the no_filter option is selected, none of the above touches will be deleted
and every touch that is stored in the _raw.txt file will be included in the
_touches.txt files.
"""

# Import the necessary modules
import argparse, glob, os, sys
import numpy as np
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime

# Set up argparse
parser = argparse.ArgumentParser()
parser.add_argument('input', help = 'filename or folder containing input data \
(*_raw.txt)',
type = str)
touch_filter = parser.add_mutually_exclusive_group(required=False)
touch_filter.add_argument('-t', '--threshold', help = 'exclude touches of which the \
duration is shorter than a specified duration (in s)',
type = float)
touch_filter.add_argument('-nf', '--no_filter', help = 'do not exclude any \
touches, even if they may belong to the same foot fault',
action = 'store_true')
args = parser.parse_args()

# Check that the input arguments make sense
if args.input[-8:] == '_raw.txt' and os.path.isfile(args.input):
    # Input argument is a single file
    file_list = [args.input]
elif os.path.isdir(args.input):
    # Input argument is a folder
    # Add a forward slash if not already provided
    if args.input[-1] != '/':
        args.input += '/'
    # Add all files ending in _raw.txt to file_list
    file_list = glob.glob('{}*_raw.txt'.format(args.input))
    if not file_list:
        print('Error: No *_raw.txt files found in input folder.')
        sys.exit()
else:
    print('Error: Input file or folder does not exist.')
    sys.exit()

# Define a threshold; touches with a duration shorter than this threshold will
# be filtered out
if args.threshold:
    threshold = args.threshold
    if args.threshold > 0.1:
        print('Warning: threshold option is set at {} s. This may \
        accidentally exclude many foot faults.'.format(args.threshold))
# If threshold is not defined by the user, use 0.1 s as threshold but do not
# actually filter out shorter touches (give warnings instead)
else:
    threshold = 0.1

# Extract the path from the filename(s) if this was included in args.input
slashes = [i for i, c in enumerate(args.input) if c == '/']
if slashes:
    path = args.input[:max(slashes)+1]
else:
    path = ''
# Create an alphabetically sorted list of files for processing
file_list = sorted([filename[len(path):] for filename in file_list])

# Make a logger that writes all warnings and filtered touches to a log.txt file
def log(msg, path, *args): # *args: filename, channel, time, duration, threshold
    date = datetime.now().strftime('%Y%m%d')
    file_out = path + 'log.txt'
    if msg == 'warning':
        output = '{} {}: Warning! Touch on ch{} at time = {} s has duration {} s.\n'.format(date, *args)
    elif msg == 'delete':
        output = '{} {}: Deleted short touch on ch{} at time = {} s with duration {} s (threshold set at {} s).\n'.format(date, *args)
    elif msg == 'repeated':
        output = '{} {}: Deleted repeated touch on ch{} at time = {} s with duration {} s.\n'.format(date, *args)
    elif msg == 'double':
        output = '{} {}: Deleted touch on ch{} at time {} s coinciding within 150 ms with a touch on ch{}.\n'.format(date, *args)
    else:
        output = '{} {}: {}'.format(date,filename,msg)
    with open(file_out,'a') as f:
        f.write(output)

# Process the _raw.txt file(s)
for filename in file_list:

    # Force import as 2D array in case no touch was recorded
    # (i.e., only a single row in _raw.txt file)
    temp_data = np.array(np.genfromtxt(path+filename,delimiter=','),ndmin=2)
    if np.shape(temp_data)[0] <= 1:
        # This should not happen as for each successful trial at least the
        # start and finish electrodes should have been touched
        print('Error processing {}: No touches detected.'.format(filename))
        sys.exit(1)
    # Number of MPR121s sensors, in case less than 4 sensors were used
    n_MPR121s = np.shape(temp_data)[1] - 1

    # Now re-import the data from the _raw.txt file using the right data types
    data = np.genfromtxt(path+filename,delimiter=',',
    dtype='float'+ n_MPR121s*',int')
    nrows = len(data)
    ncols =  n_MPR121s*12+1
    newdata = np.zeros((nrows,ncols))
    start_ch = 47
    finish_ch = 0

    # Rearrange the data to show the touch status for each channel individually
    for row in range(nrows):
        newdata[row][0] = data[row][0] # Copy timestamp to the new data array
        touch_list = []
        for MPR121 in range(n_MPR121s):
            # Convert touch status to list of integers with values 0 or 1
            touch_list.extend(list(reversed(
            [int(d) for d in str(format(data[row][MPR121+1],'#014b')[2:])])))
        newdata[row][1:ncols] = touch_list # Paste the list to new data array

    touches = np.zeros((0,4)) # Empty array to be filled with touch data
    temp = {} # Container to store the touched channels and starting times
    start = newdata[0][0] # Start time relative to start of data collection

    # Check that no electrodes were touched during the first measurement
    if sum(newdata[0][1:ncols]) != 0:
        print('Error processing {}: One or more sensors were touched during \
        start of data collection. Please check the raw data file and try again.\
        '.format(filename))
        sys.exit(1)

    # For each touch, calculate time relative to first touch and the duration
    # Exclude the first row here (which should be empty except for time)
    for row in range(1,nrows):

        for ch in range(ncols-1):

            include_touch = True # By default, include all touches
            if newdata[row][ch+1] == 1 and newdata[row-1][ch+1] == 0: # Touched
                if row == 1 and ch != start_ch:
                    msg = ('Warning! First touch was recorded on channel {}.\n'.format(ch))
                    log(msg, path, filename)

                time = newdata[row][0] - start

                # Keep the channel and time of each touch until until the
                # corresponding touch is released and duration can be calculated
                temp.update({ch:time})

            elif newdata[row][ch+1] == 0 and newdata[row-1][ch+1] == 1: # Touch released
                released = newdata[row][0] - start
                duration = released - temp[ch]
                if duration < threshold and finish_ch < ch < start_ch:
                    log_ch = int(ch)
                    log_time = Decimal(str(temp[ch])).quantize(Decimal('.001'), rounding=ROUND_HALF_UP)
                    log_dur = Decimal(str(duration)).quantize(Decimal('.001'), rounding=ROUND_HALF_UP)
                    if args.threshold:
                        log('delete', path, filename, log_ch, log_time, log_dur, threshold)
                        include_touch = False
                    else:
                        log('warning', path, filename, log_ch, log_time, log_dur)
                if include_touch:
                    touches = np.vstack([touches,[0,ch,temp[ch],duration]])
                del temp[ch]

    # Sort the touches by starting time
    touches = touches[np.argsort(touches[:,2])]

    # Filter out touches that likely belong to the same foot fault
    if not args.no_filter:
        import filters

        # Delete any touches that occur on the same channel within 0.150 s
        touches, deleted = filters.repeated_touches(touches, repeated_touch_threshold = 0.150)
        if deleted.any():
            for index, row in enumerate(deleted):
                log_ch = int(row[1])
                log_time = Decimal(str(row[2])).quantize(Decimal('.001'), rounding=ROUND_HALF_UP)
                log_dur = Decimal(str(row[3])).quantize(Decimal('.001'), rounding=ROUND_HALF_UP)
                log('repeated', path, filename, log_ch, log_time, log_dur)

        # Also delete any touches that occur almost simultaneously on two adjacent channels
        touches, deleted = filters.double_electrode(touches)
        if deleted.any():
            for index, row in enumerate(deleted):
                log_ch = int(row[1])
                log_time = Decimal(str(row[2])).quantize(Decimal('.001'), rounding=ROUND_HALF_UP)
                log_dur = Decimal(str(row[3])).quantize(Decimal('.001'), rounding=ROUND_HALF_UP)
                log('double', path, filename, log_ch, log_time, log_ch+2)

    # Give each touch an index
    touch_numbers = len(touches)
    touches[:,0] = [d+1 for d in range(touch_numbers)]

    # Change the filename to touches_filtered.txt if filtering was done and save
    if args.no_filter:
        touches_filename = '{}{}_touches_no_filter.txt'.format(path,filename[:-8])
    else:
        touches_filename = '{}{}_touches.txt'.format(path,filename[:-8])
    hdr_touches = 'touch,ch,time,duration'
    np.savetxt(touches_filename, touches, fmt='%i,%i,%.3f,%.3f',newline='\n',header=hdr_touches,comments='')

if len(file_list) > 1:
    print('\nDone processing {} files.'.format(len(file_list)))
else:
    print('\nProcessed {} with {} MPR121 sensor(s) ({} channels).'.format(path+filename, n_MPR121s, n_MPR121s*12))
