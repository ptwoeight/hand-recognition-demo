# name=Gesture Controller Script

import mixer

# CC_Number : Insert_Index
CC_INSERT_MAP = {
    21: 1,
    22: 2,
    23: 3, 
    24: 4,
    25: 5
}
ARM_CC = 35

def OnControlChange(e):
    # 1. Filter for our specific CCs
    if e.data1 in CC_INSERT_MAP:
        target_insert = CC_INSERT_MAP[e.data1]
        
        # Get and Toggle state
        current_state = mixer.isTrackEnabled(target_insert)
        mixer.enableTrack(target_insert, not current_state)
        
        # This will show up in the Script Output window
        print(f"Handled CC {e.data1}: Toggled Insert {target_insert}")
        
        e.handled = True

    # 2. Handle Arming
    elif e.data1 == ARM_CC:
        current_track = mixer.trackNumber()
        is_armed = mixer.isTrackArmed(current_track)
        mixer.armTrack(current_track, not is_armed)
        
        print(f"Handled CC {e.data1}: Toggled Arm on Track {current_track}")
        
        e.handled = True