# name=Gesture Controller
import mixer

# CC MAPPING RANGES:
# 21-25: select mixer track 1-5
# 31-35: toggle ARM on track 1-5
# 41-45: toggle MUTE on track 1-5
# 20:    volume automation on current track

def OnControlChange(e):
    cc_num = e.data1
    value = e.data2 # 0-127

    # --- LOGIC A: SELECT TRACK (CC 21-25) ---
    if 21 <= cc_num <= 25:
        target_track = cc_num - 20 # Maps 21->1, 22->2, etc.
        mixer.setTrackNumber(target_track)
        e.handled = True

    # --- LOGIC B: TOGGLE ARM (CC 31-35) ---
    elif 31 <= cc_num <= 35:
        target_track = cc_num - 30 # Maps 31->1, 32->2, etc.
        is_armed = mixer.isTrackArmed(target_track)
        mixer.armTrack(target_track, not is_armed)
        e.handled = True

    # --- LOGIC C: TOGGLE MUTE (CC 41-45) ---
    elif 41 <= cc_num <= 45:
        target_track = cc_num - 40 # Maps 41->1, 42->2, etc.
        # In FL MIDI Scripting, 0 = Active, 1 = Muted
        is_muted = mixer.isTrackMuted(target_track)
        mixer.muteTrack(target_track, not is_muted)
        e.handled = True

    # --- LOGIC D: VOLUME AUTOMATION (CC 20) ---
    elif cc_num == 20:
        current_track = mixer.trackNumber()
        # Scale MIDI 0-127 to FL's internal 0.0-1.0 float
        volume_val = value / 127 
        mixer.setTrackVolume(current_track, volume_val)
        e.handled = True