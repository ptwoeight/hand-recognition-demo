# name=Gesture Controller Script (MUTE)
import mixer

CC_INSERT_MAP = {
    21: 1, 22: 2, 23: 3, 24: 4, 25: 5,  # Mute/Enable Range
    31: 1, 32: 2, 33: 3, 34: 4, 35: 5   # Arming Range
}
AUTOMATION_CC = 20

def OnControlChange(e):
    # Check if the incoming CC is in our map
    if e.data1 in CC_INSERT_MAP:
        target_insert = CC_INSERT_MAP[e.data1]
        # LOGIC A: Toggle Mute/Enable (CCs 21-25)
        if 21 <= e.data1 <= 25:
            current_state = mixer.isTrackEnabled(target_insert)
            mixer.enableTrack(target_insert, not current_state)
            print(f"Handled CC {e.data1}: Toggled Mute on Insert {target_insert}")
        
        # LOGIC B: Toggle Arming (CCs 31-35)
        elif 31 <= e.data1 <= 35:
            is_armed = mixer.isTrackArmed(target_insert)
            mixer.armTrack(target_insert, not is_armed)
            print(f"Handled CC {e.data1}: Toggled Arm on Insert {target_insert}")
        
        # Mark as handled so FL doesn't use generic mapping
        e.handled = True
        