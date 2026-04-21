import math
import cv2
from enum import Enum

# == [1] CONFIGS + CONSTANTS == #
MUTE_BASE_CC = 40   # CC 41-45 (Mute)
ARM_BASE_CC = 30    # CC 31-35 (Arm)
SELECT_BASE_CC = 20 # CC 21-25 (Select)

PINK = (120, 29, 222)
""" THRESHOLD_extended = 0.12
THRESHOLD_thumb_curl = 0.02 """

class FingerState(Enum):
    UNKNOWN = 0
    EXTENDED = 1
    CURLED = 2

def calculate_distance(point1, point2):
    return math.sqrt((point2.x - point1.x)**2 + (point2.y - point1.y)**2)

previous_gesture = ""

def process_logic(hand_landmarks, hand_handedness, midi_handler, width, height, mp_hands, frame, state):
    global previous_gesture
    
    lm = hand_landmarks.landmark
    idx_tip, idx_mcp = lm[mp_hands.HandLandmark.INDEX_FINGER_TIP], lm[mp_hands.HandLandmark.INDEX_FINGER_MCP]
    mid_tip, mid_mcp = lm[mp_hands.HandLandmark.MIDDLE_FINGER_TIP], lm[mp_hands.HandLandmark.MIDDLE_FINGER_MCP]
    rng_tip, rng_mcp = lm[mp_hands.HandLandmark.RING_FINGER_TIP], lm[mp_hands.HandLandmark.RING_FINGER_MCP]
    pky_tip, pky_mcp = lm[mp_hands.HandLandmark.PINKY_TIP], lm[mp_hands.HandLandmark.PINKY_MCP]
    thumb_tip = lm[mp_hands.HandLandmark.THUMB_TIP]

    idx_state = FingerState.EXTENDED if calculate_distance(idx_tip, idx_mcp) > state.calib_extended else FingerState.CURLED
    mid_state = FingerState.EXTENDED if calculate_distance(mid_tip, mid_mcp) > state.calib_extended else FingerState.CURLED
    rng_state = FingerState.EXTENDED if calculate_distance(rng_tip, rng_mcp) > state.calib_extended else FingerState.CURLED
    pky_state = FingerState.EXTENDED if calculate_distance(pky_tip, pky_mcp) > state.calib_extended else FingerState.CURLED

    # 3. Thumb State Detection
    thumb_x_diff = thumb_tip.x - idx_mcp.x
    if hand_handedness == "Right": thumb_x_diff = -thumb_x_diff
    thumb_curled = thumb_x_diff < state.calib_thumb_curl

    # 4. Gesture Logic Execution
    all_fingers_down = (idx_state == FingerState.CURLED and mid_state == FingerState.CURLED and 
                        rng_state == FingerState.CURLED and pky_state == FingerState.CURLED)
    gesture_label = "No Toggle Detected"
    target_cc = None    
    
    # --- [RESET LOGIC (Applies to both hands)] ---
    # Check if hand is fully open (neutral state)
    hand_open = not all_fingers_down and not thumb_curled
    
    if hand_open:
        gesture_label = "No Toggle Detected"
        previous_gesture = "" 

    # --- [LEFT HAND: NAVIGATION] ---
    if hand_handedness == "Left":
        # Move LEFT (Index, Mid, Ring, Pinky DOWN)
        if all_fingers_down and not thumb_curled:
            gesture_label = "NAV: Left (Prev)"
            if gesture_label != previous_gesture:
                new_insert = 5 if midi_handler.active_insert <= 1 else midi_handler.active_insert - 1
                midi_handler.set_active_insert(new_insert)
                midi_handler.send_toggle(20 + new_insert, True)
                previous_gesture = gesture_label

        # Move RIGHT (Thumb DOWN)
        elif thumb_curled and not all_fingers_down:
            gesture_label = "NAV: Right (Next)"
            if gesture_label != previous_gesture:
                new_insert = (midi_handler.active_insert % 5) + 1
                midi_handler.set_active_insert(new_insert)
                midi_handler.send_toggle(20 + new_insert, True)
                previous_gesture = gesture_label

    # --- [RIGHT HAND: TOGGLE ACTIONS] ---
    else:
        # Toggle MUTE (All fingers down)
        if all_fingers_down and not thumb_curled:
            gesture_label = "Toggle MUTE"
            if gesture_label != previous_gesture:
                midi_handler.send_toggle(40 + midi_handler.active_insert, True)
                previous_gesture = gesture_label

        # Toggle ARM (Thumb down)
        elif thumb_curled and not all_fingers_down:
            gesture_label = "Toggle ARM"
            if gesture_label != previous_gesture:
                midi_handler.send_toggle(30 + midi_handler.active_insert, True)
                previous_gesture = gesture_label

    return gesture_label




