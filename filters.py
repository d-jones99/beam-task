# Last edited May 31st, 2017

import numpy as np

def repeated_touches(touches, repeated_touch_threshold):
    """This function filters out touches on the same electrode channel that
    occur within a certain given amount of time. Usually, repeated touches are
    caused by a mouse repositioning its foot on the side ledge and therefore
    should not count as separate foot faults.

    Input arguments
    touches: a 2D numpy array containing the individual touch data
    repeated_touch_threshold: the threshold (in seconds) that determines how
    close in time repeated touches onto the same channel have to be in order to
    be filtered out

    Output
    no_rt: a 2D numpy array containing the filtered individual touch data
    deleted: a 2D numpy array containing the deleted touch data"""

    # Get all channels in which more than 1 touch occured
    unique, counts = np.unique(touches[:,1], return_counts=True)
    repeated_touched_channels = [unique[index] for index, count in enumerate(counts) if count > 1]

    # Get a boolean mask of rows of which the channel is in repeated_touched_channels
    mask = np.in1d(touches[:,1].ravel(), repeated_touched_channels).reshape(touches[:,1].shape)

    # rt is equal to all the rows in touches for which the mask is True
    rt = touches[mask]
    rt = rt[np.argsort(rt[:,2])][::-1] # order so that first touch comes last

    # no_rt is equal to all the rows in touches for which the mask is False
    no_rt = touches[~mask]

    # Keep an array of all touches that are deleted
    deleted = np.zeros([0,4])

    # For each channel, remove the shortest touch of pairs that follow each
    # other within the repeated_touch_threshold
    for ch in repeated_touched_channels:

        subarray = rt[np.where(rt[:,1] == ch)]
        stop = False

        while len(subarray) > 1 and stop == False:

            # While there are still multiple touches left, compare the start
            # time of each touch against the next one. If a touch is to be
            # deleted, restart the loop. If no touch is deleted, exit the while
            # loop
            for row in range(len(subarray)):

                # If the difference between start times of both touches is
                # smaller than or equal to the threshold...
                if subarray[row,2] - subarray[row+1,2] <= repeated_touch_threshold:
                    # And 1) the duration of the first touch is smaller than
                    # that of the second one, or 2) it is the start channel (47):
                    if subarray[row,3] < subarray[row+1,3] or subarray[row,1] == 47:
                        # Delete the first (=shorter) touch
                        deleted = np.vstack([deleted, subarray[row]])
                        subarray = np.delete(subarray,row,0)
                        # If there is only 1 touch left:
                        if len(subarray) < 2:
                            no_rt = np.vstack([no_rt, subarray]) # keep that touch
                        # Restart the for loop with the updated subarray
                        break
                    # Else 1) if the duration of the first touch is greater than
                    # that of the second one, or 2) it is the finish channel (0)
                    elif subarray[row,3] >= subarray[row+1,3] or subarray[row,1] == 0:
                        # Delete the second (=shorter) touch
                        deleted = np.vstack([deleted, subarray[row+1]])
                        subarray = np.delete(subarray,row+1,0)
                        # If there is only 1 touch left:
                        if np.shape(subarray)[0] < 2:
                            no_rt = np.vstack([no_rt, subarray]) # keep that touch
                        # Restart the for loop with the updated subarray
                        break
                # If no multiple touches remain and, as a result, the for loop
                # continued until the last pair of rows:
                elif row == len(subarray) - 2:
                    # Add the remaining touches to the no_rt array
                    no_rt = np.vstack([no_rt, subarray])
                    # Break the while loop and go to the next channel (in the
                    # outer for loop)
                    stop = True
                    break

    # Restore the initial order of touches
    no_rt = no_rt[np.argsort(no_rt[:,2])]
    deleted = deleted[np.argsort(deleted[:,2])]

    return no_rt, deleted

def double_electrode(touches):
    """This function filters out touches that occured shortly after each other
    on two adjacent electrode channels, which indicates that a mouse put its
    paw onto both electrodes (almost) simultaneously. In most cases, this is a
    single touch and so it should not count as two foot faults. The touch to
    be deleted is the one closest to the narrow end of the beam.

    Input argument
    touches: a 2D numpy array containing the individual touch data

    Output
    no_de: a 2D numpy array containing the filtered individual touch data
    deleted: a 2D numpy array containing the deleted touch data"""

    # Keep an array of all touches that are deleted
    deleted = np.zeros([0,4])

    while True:

        touch_deleted = False
        # For each touch, obtain an array of other touches that started within
        # 150 ms after the start of that touch
        for row in range(len(touches)):
            # Select all touches after the current one
            subarray = touches[row+1:]
            # Keep all touches that started at or before 150 ms after current touch
            within_time = subarray[np.where(subarray[:,2] <= touches[row][2] + 0.150)]

            # For each touch in the array, check whether or not the absolute
            # difference in channel is 2 (e.g. 6 and 4, or 6 and 8). If true,
            # these electrodes are adjacent along the length of the beam.
            # The only exceptions are the start and finish electrodes.
            for row2 in range(len(within_time)): # only loops if within_time is not null
                ch_1 = touches[row][1]
                ch_2 = within_time[row2][1]
                if abs(ch_1 - ch_2) == 2 and (ch_1 and ch_2 not in [0,47]):

                    # If so, delete the touch(es) corresponding to the lowest
                    # channel number (e.g the one closest to the finish)
                    if ch_1 < ch_2:
                        deleted = np.vstack([deleted, touches[row]])
                        touches = np.delete(touches, row, 0)
                        touch_deleted = True
                        break
                    else:
                        deleted = np.vstack([deleted, within_time[row2]])
                        touches = np.delete(touches, row+row2+1, 0)
                        touch_deleted = True
                        break

            # If a touch has been deleted during the inner loop,
            # break from the outer loop as well and restart with updated array
            if touch_deleted == True:
                break

        # 4. Keep looping until no touch has been deleted anymore
        if touch_deleted == False:
            no_de = touches
            break

    return no_de, deleted
