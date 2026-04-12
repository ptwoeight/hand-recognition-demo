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
    # Landmark mapping
    thumb_tip, index_mcp = lm[4], lm[5]
    index_tip, middle_tip = lm[8], lm[12]
    ring_tip, pinky_tip = lm[16], lm[20]
    index_base, middle_base = lm[5], lm[9]
    ring_base, pinky_base = lm[13], lm[17]

    # Finger states (Curled = Down)
    idx_down = calculate_distance(index_tip, index_base) < state.calib_curled
    mid_down = calculate_distance(middle_tip, middle_base) < state.calib_curled
    rng_down = calculate_distance(ring_tip, ring_base) < state.calib_curled
    pky_down = calculate_distance(pinky_tip, pinky_base) < state.calib_curled

    # Thumb logic
    thumb_x_diff = thumb_tip.x - index_mcp.x
    if hand_handedness == "Right": thumb_x_diff = -thumb_x_diff
    thumb_down = thumb_x_diff < state.calib_thumb_curl

    gesture_label = "Scanning..."
    target_cc = None

    # --- [RESET LOGIC (Applies to both hands)] ---
    # Check if hand is fully open (neutral state)
    hand_open = not idx_down and not mid_down and not rng_down and not pky_down and not thumb_down
    
    if hand_open:
        gesture_label = "Scanning..."
        previous_gesture = "" # This "unlocks" the sensors for the next gesture

    # --- [LEFT HAND: NAVIGATION] ---
    if hand_handedness == "Left":
        # Move LEFT (Index, Mid, Ring, Pinky DOWN)
        if idx_down and mid_down and rng_down and pky_down and not thumb_down:
            gesture_label = "NAV: Left (Prev)"
            if gesture_label != previous_gesture:
                new_insert = 5 if midi_handler.active_insert <= 1 else midi_handler.active_insert - 1
                midi_handler.set_active_insert(new_insert)
                midi_handler.send_toggle(20 + new_insert, True)
                previous_gesture = gesture_label

        # Move RIGHT (Thumb DOWN)
        elif thumb_down and not (idx_down and mid_down and rng_down and pky_down):
            gesture_label = "NAV: Right (Next)"
            if gesture_label != previous_gesture:
                new_insert = (midi_handler.active_insert % 5) + 1
                midi_handler.set_active_insert(new_insert)
                midi_handler.send_toggle(20 + new_insert, True)
                previous_gesture = gesture_label

    # --- [RIGHT HAND: TOGGLE ACTIONS] ---
    else:
        # Toggle MUTE (All fingers down)
        if idx_down and mid_down and rng_down and pky_down and not thumb_down:
            gesture_label = "Action: Toggle MUTE"
            if gesture_label != previous_gesture:
                midi_handler.send_toggle(40 + midi_handler.active_insert, True)
                previous_gesture = gesture_label

        # Toggle ARM (Thumb down)
        elif thumb_down and not (idx_down and mid_down and rng_down and pky_down):
            gesture_label = "Action: Toggle ARM"
            if gesture_label != previous_gesture:
                midi_handler.send_toggle(30 + midi_handler.active_insert, True)
                previous_gesture = gesture_label

    return gesture_label