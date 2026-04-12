import math

def calculate_distance(p1, p2):
    return math.sqrt((p2.x - p1.x)**2 + (p2.y - p1.y)**2)

def process_calibration(hand_landmarks, state, mp_hands):
    lm = hand_landmarks.landmark

    thumb_tip = lm[mp_hands.HandLandmark.THUMB_TIP]
    thumb_mcp = lm[mp_hands.HandLandmark.THUMB_MCP]
    index_tip = lm[mp_hands.HandLandmark.INDEX_FINGER_TIP]
    index_mcp = lm[mp_hands.HandLandmark.INDEX_FINGER_MCP]

    # Raw Measurements
    dist_index = calculate_distance(index_tip, index_mcp)
    thumb_to_index_mcp = calculate_distance(thumb_tip, index_mcp)
    thumb_y_diff = thumb_mcp.y - thumb_tip.y
    max_stretch_dist = calculate_distance(thumb_tip, index_tip) 

    #  STEP 1: CLOSED (OPEN FIST LIKE SHOWING NAILS)
    if state.calibration_step == 1:
        # set it slightly above raw distance
        state.calib_curled = dist_index + 0.01
        state.calib_thumb_curl = thumb_to_index_mcp + 0.01

        state.calib_smoothing_factor = 0.2      # default for stable hands

        # return "STEP 1: Curl fingers into an open fist. Click 'NEXT'."
    
    # STEP 2: OPEN (EXTENDED FINGERS)
    elif state.calibration_step == 2:
        # ceiling values; set slightly below full ext
        state.calib_extended = dist_index - 0.02
        state.calib_thumb_y_extend = thumb_y_diff - 0.01
        state.calib_max_stretch = max_stretch_dist

        # return "STEP 2: Stretch hand wide. Click 'NEXT'."
    
    else:
        return "CALIBRATION COMPLETE! See menu window."