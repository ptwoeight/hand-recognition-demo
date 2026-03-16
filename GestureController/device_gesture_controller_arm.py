# name=Gesture Controller Script (ARM)
import mixer

CC_INSERT_MAP = {
    21: 1, 22: 2, 23: 3, 24: 4, 25: 5,  # Selection Range
    31: 1, 32: 2, 33: 3, 34: 4, 35: 5   # Arming Range
}
AUTOMATION_CC = 20

def OnControlChange(e):
    # LOGIC A: Change Track Selection (CCs 21-25)
    if e.data1 in CC_INSERT_MAP and 21 <= e.data1 <= 25:
        target_insert = CC_INSERT_MAP[e.data1]
        mixer.setTrackNumber(target_insert)
        e.handled = True

    # LOGIC B: Toggle Arming (CCs 31-35)
    elif e.data1 in CC_INSERT_MAP and 31 <= e.data1 <= 35:
        target_insert = CC_INSERT_MAP[e.data1]
        is_armed = mixer.isTrackArmed(target_insert)
        mixer.armTrack(target_insert, not is_armed)
        e.handled = True

    # LOGIC C: Dynamic Volume Automation (CC 20)
    elif e.data1 == AUTOMATION_CC:
        # This targets the CURRENTLY SELECTED track's volume fader
        current_track = mixer.trackNumber()
        # Scale MIDI 0-127 to FL's internal 0.0-1.0 float
        volume_val = e.data2 / 127 
        mixer.setTrackVolume(current_track, volume_val)
        e.handled = True