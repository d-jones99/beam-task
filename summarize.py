# Last edited June 15, 2017
# Important: this script assumes 4 MPR121 sensors (48 channels in total)

"""This script will integrate all data stored in _touches.txt files into
a single summary file. By default, the user is prompted to provide 1) the
first data folder to include, 2) the total number of folders, and 3)
the time interval (in days) between those folders. This approach has been
implemented with daily test sessions of three trials per day in mind.
Alternatively, the user can input the data folders manually by using the -m
option, or change the number of trials per day by using the -t option followed
by an integer representing the number of trials to include. A different output
filename can be chosen by using the -o option followed by the desired output
filename (without .txt extension)."""

import os, glob, sys, argparse
import numpy as np
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP

# Some variables to define
start_ch = 47
finish_ch = 0

# Set up argparse
parser = argparse.ArgumentParser()
parser.add_argument('-o', '--out', help = 'output filename (without extension)', type = str)
parser.add_argument('-t', '--trials', help = 'number of trials', type = int)
parser.add_argument('-m', '--manual', help = 'input each data folder manually', action = 'store_true')
args = parser.parse_args()

# Check optional arguments
if args.trials:
    trials = args.trials
else:
    trials = 3
if args.out:
    out = args.out
else:
    out = 'summary'
if os.path.isfile('data/{}.txt'.format(out)):
    while True:
        overwrite = input('Output file already exists, do you want to delete the existing file now? [y/n] ').lower()
        if overwrite not in ('y', 'n'):
            print('Invalid answer, please try again.')
        elif overwrite == 'y':
            print('Continuing: data/{}.txt has been deleted'.format(out))
            os.remove('data/{}.txt'.format(out))
            os.remove('data/{}_log.txt'.format(out))
            break
        elif overwrite == 'n':
            input('Exiting.')
            sys.exit(1)

# Ask for input arguments
def is_number(s):
    try:
        float(s)
        return True
    except ValueError:
        return False

if args.manual:
    while True:
        folders = input('Enter data folders to include, separated by spaces: ').split()
        for folder in folders:
            if len(folder) != 8 or is_number(folder) == False:
                print("Error in folder name '{}': format should be YYYYMMDD. Please try again.".format(folder))
                folders = []
        if folders:
            break

else:
    while True:
        start_date = input('First data folder to include: ')
        if len(start_date) != 8 or is_number(start_date) == False:
            print('Format should be YYYYMMDD. Please try again.')
        else:
            start_date = datetime.strptime(start_date,"%Y%m%d")
            break

    while True:
        num_folders = input('Total number of data folders to include: ')
        if is_number(num_folders) == False:
            print('Input should be a number. Please try again.')
        else:
            num_folders = int(num_folders)
            break

    while True:
        interval = input('Interval between data folders: ')
        if is_number(interval) == False:
            print('Input should be a number. Please try again.')
        else:
            interval = int(interval)
            break

    all_dates = [start_date + timedelta(interval)*i for i in range(num_folders)]
    folders = [date.strftime("%Y%m%d") for date in all_dates]

print('\nIncluding the following folders with {} trials per day: {}.'.format(trials,', '.join(folders)))
input('Press Enter to continue...')

# Get all the different subjects in each folder
unique_subjects = {}
all_subjects = []
for folder in folders:
    file_list = glob.glob('data/{}/*_touches.txt'.format(folder))
    subjects_found = [path[14:-16] for path in file_list]
    unique_subjects[folder] = list(set(subjects_found))
    all_subjects += subjects_found

unique_subjects['total'] = list(set(all_subjects))

# Check whether all unique subjects are found in all folders
subjects_complete = []
subjects_incomplete = {}

# For all subjects in total:
# Check if subject exist in folder for all folders
# If doesn't exist in a folder, put that info in subjects_incomplete and add 'missing' flag
# If subject doesn't have 'missing' flag, add it to subjects_complete

for subject in unique_subjects['total']:
    complete = True
    for folder in folders:
        if subject not in unique_subjects[folder]:
            complete = False
            if folder in subjects_incomplete:
                subjects_incomplete[folder].append(subject)
            else:
                subjects_incomplete[folder] = [subject]
    if complete == True:
        subjects_complete.append(subject)

subjects_complete.sort()
subjects_incomplete = sorted(subjects_incomplete.items())

if not subjects_complete:
    print('\nError: could not find subjects with data for all dates specified.')
    sys.exit(1)

if subjects_incomplete:
    print('\nWarning: the following subject(s) could not be found:')
    for m in range(len(subjects_incomplete)):
        folder = subjects_incomplete[m][0]
        print('{}: {}'.format(folder,', '.join(subjects_incomplete[m][1])))
    input('Press Enter to continue...')

print('\nThe following subjects were found:') #TODO: maybe print in columns?
for subject in subjects_complete:
    print(subject)
input('Press Enter to continue...')

subjects = subjects_complete

# Check first that all files exist (for folders, for subjects, for trials)
non_existent_files = []
for folder in folders:
    for subject in subjects:
        for trial in range(1,trials+1):
            filename = 'data/{}/{}_{}_touches.txt'.format(folder,subject,str(trial).zfill(3))
            if not os.path.isfile(filename):
                non_existent_files.append(filename)
if non_existent_files:
    print('Error: the following file(s) could not be found:')
    for f in non_existent_files:
        print(f)
    print('\n')
    exit(1)

# Assign groups to subjects
groups = {}
for subject in subjects:
    groups[subject] = input('Assign group to {}: '.format(subject))

print('\nAll ready to go!')
input('Press Enter to continue...')
print('\nProcessing...')

# Make a logger that writes all warnings log.txt file
def log(folder, subject, trial, msg):
    output = '{}/{}_{}: {}'.format(folder, subject, str(trial).zfill(3), msg)
    with open('data/{}_log.txt'.format(out),'a') as f:
        f.write(output)

# Go through every file and add the summary statistics to summary.txt
for folder in folders:
    for subject in subjects:

        for trial in range(trials):
            filename = 'data/{}/{}_{}_touches.txt'.format(folder,subject,str(trial+1).zfill(3))
            # Read corresponding _touches.txt file
            touches = np.array(np.genfromtxt(filename,delimiter=',',skip_header=1),ndmin=2)

            # Calculate the means of the following for the number of trials per day:
            # 1) total number of foot faults
            # 2) total number of right-sided foot faults
            # 3) total number of left-sided foot faults
            # 4) traversion time
            # 5) time to first foot fault
            # 6) distance to first foot fault

            # 1), 2), and 3): number of (lateralized) foot faults
            unique, counts = np.unique(touches[:,1], return_counts=True)
            right = 0
            left = 0
            summary = np.zeros((1,48))

            for ch, count in zip(unique, counts):
                summary[0,int(ch)] = count
                if finish_ch < ch < start_ch and ch % 2 == 0: # If ch is even (and excluding the start & finish channels)
                    right += count
                elif finish_ch < ch < start_ch > 1 and ch % 2 == 1: # If ch is odd (and exluding the start & finish channels)
                    left += count
            total = left + right

            # 4) Calculate the traversion time, by substracting the time of the last touch
            # (finish_ch) from the first touch (start_ch)

            # Take the last touch recorded on start_ch
            start_touches = touches[np.where(touches[:,1] == start_ch)]
            if len(start_touches) == 0:
                msg = 'No touch recorded on channel {}. Could not calculate traversion time.\n'.format(start_ch)
                log(folder, subject, trial, msg)
                trav_time = 'nan'
                start_time = 'nan'
            else:
                # If there is at least one touch recorded on start_ch, take the last one
                # and continue with the last touch recorded (on finish_ch)
                start_time = start_touches[-1][2]

                # Get all touches on finish_ch
                finish_touches = touches[np.where(touches[:,1] == finish_ch)]
                if len(finish_touches) == 0:
                    msg = 'No touch recorded on channel {}. Could not calculate traversion time.\n'.format(finish_ch)
                    log(folder, subject, trial, msg)
                    trav_time = 'nan'
                else:
                    # If there is at least one touch recorded on finish_ch, take the
                    # release time of the first one (= touch time + duration)
                    finish_time = finish_touches[0][2] + finish_touches[0][3]

                    # If another channel was touched after release of finish_ch
                    # (perhaps by a tail or by the investigator):
                    if finish_touches[-1,2] + finish_touches[-1,3] < touches[-1,2]:
                        msg = 'At least one other channel was touched after channel {} was released. Calculation of traversion time may be incorrect.\n'.format(finish_ch)
                        log(folder, subject, trial, msg)
                    trav_time = str(finish_time - start_time)

            # 5) and 6): Time and distance to first foot fault
            if total != 0:# If there are any foot faults detected
                foot_faults = touches[np.where(touches[:,1] < start_ch)]
                foot_faults = foot_faults[np.where(foot_faults[:,1] > finish_ch)]
                dist_to_first_fault = str(int(100 - (foot_faults[0,1] // 2) * 4))
                if start_time != 'nan': # If start time was not recorded, time to first
                # foot fault is not defined
                    time_to_first_fault = str(foot_faults[0,2] - start_time)
                    time_to_first_fault = str(Decimal(time_to_first_fault).quantize(Decimal('.001'), rounding=ROUND_HALF_UP))
                else:
                    time_to_first_fault = 'nan'
            else:
                time_to_first_fault = 'nan'
                dist_to_first_fault = 'nan'

            # Add the results to summary.txt file
            summary_txt = '\n' + ','.join((folder,groups[subject],subject,str(trial+1),str(total),str(left),str(right),trav_time,time_to_first_fault,dist_to_first_fault))
            if not os.path.isfile('data/{}.txt'.format(out)):
                summary_txt = 'day,group,subject,trial,total,left,right,trav_time,time_to_first,dist_to_first' + summary_txt
            with open('data/{}.txt'.format(out),'a') as f:
                f.write(summary_txt)
print('\nSaved to /data/{}.txt'.format(out))
