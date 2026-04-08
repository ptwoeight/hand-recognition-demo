import math
import cv2  # Added for drawing the line
from enum import Enum

# == [1] CONFIGS + CONSTANTS == #
INSERT_1_CC = 21
INSERT_2_CC = 22
INSERT_3_CC = 23
INSERT_4_CC = 24
INSERT_5_CC = 25
ARM_BASE_CC = 30  
AUTOMATION_CC = 20

PINK = (120, 29, 222)
THRESHOLD_extended = 0.12
THRESHOLD_thumb_curl = 0.02
THRESHOLD_thumb_y_extend = 0.09
SMOOTHING_FACTOR = 0.2

class FingerState(Enum):
    UNKNOWN = 0
    EXTENDED = 1
    CURLED = 2

class Point:
    def __init__(self, x, y):
        self.x = x
        self.y = y

def calculate_distance(point1, point2):
    return math.sqrt((point2.x - point1.x)**2 + (point2.y - point1.y)**2)

previous_gesture = ""
automation_smoothed = 0.0

def process_logic(hand_landmarks, hand_handedness, midi_handler, width, height, mp_hands, frame):
    global previous_gesture, automation_smoothed
    
    lm = hand_landmarks.landmark
    thumb_tip = lm[mp_hands.HandLandmark.THUMB_TIP]
    thumb_mcp = lm[mp_hands.HandLandmark.THUMB_MCP]
    index_tip = lm[mp_hands.HandLandmark.INDEX_FINGER_TIP]
    index_mcp = lm[mp_hands.HandLandmark.INDEX_FINGER_MCP]
    middle_tip = lm[mp_hands.HandLandmark.MIDDLE_FINGER_TIP]
    middle_mcp = lm[mp_hands.HandLandmark.MIDDLE_FINGER_MCP]
    ring_tip = lm[mp_hands.HandLandmark.RING_FINGER_TIP]
    ring_mcp = lm[mp_hands.HandLandmark.RING_FINGER_MCP]
    pinky_tip = lm[mp_hands.HandLandmark.PINKY_TIP]
    pinky_mcp = lm[mp_hands.HandLandmark.PINKY_MCP]

    dist_index = calculate_distance(index_tip, index_mcp)
    dist_middle = calculate_distance(middle_tip, middle_mcp)
    dist_ring = calculate_distance(ring_tip, ring_mcp)
    dist_pinky = calculate_distance(pinky_tip, pinky_mcp)

    thumb_x_diff = thumb_tip.x - index_mcp.x
    if hand_handedness == "Right":
        thumb_x_diff = -thumb_x_diff
    thumb_y_diff = thumb_mcp.y - thumb_tip.y

    if thumb_x_diff < THRESHOLD_thumb_curl:
        thumb_state = FingerState.CURLED
    elif thumb_y_diff > THRESHOLD_thumb_y_extend:
        thumb_state = FingerState.EXTENDED
    else:
        thumb_state = FingerState.UNKNOWN

    index_state = FingerState.EXTENDED if dist_index > THRESHOLD_extended else FingerState.CURLED
    middle_state = FingerState.EXTENDED if dist_middle > THRESHOLD_extended else FingerState.CURLED
    ring_state = FingerState.EXTENDED if dist_ring > THRESHOLD_extended else FingerState.CURLED
    pinky_state = FingerState.EXTENDED if dist_pinky > THRESHOLD_extended else FingerState.CURLED

    gesture_label = "No Toggle Detected."
    target_cc = None
    target_insert = None

    if hand_handedness == "Left":
        if index_state == FingerState.CURLED and middle_state == FingerState.EXTENDED and ring_state == FingerState.EXTENDED and pinky_state == FingerState.EXTENDED:
            gesture_label, target_cc, target_insert = "Index: Insert 1", INSERT_1_CC, 1
        elif index_state == FingerState.EXTENDED and middle_state == FingerState.CURLED and ring_state == FingerState.EXTENDED and pinky_state == FingerState.EXTENDED:
            gesture_label, target_cc, target_insert = "Middle: Insert 2", INSERT_2_CC, 2
        elif index_state == FingerState.EXTENDED and middle_state == FingerState.EXTENDED and ring_state == FingerState.CURLED and pinky_state == FingerState.EXTENDED:
            gesture_label, target_cc, target_insert = "Ring: Insert 3", INSERT_3_CC, 3
        elif index_state == FingerState.EXTENDED and middle_state == FingerState.CURLED and ring_state == FingerState.CURLED and pinky_state == FingerState.EXTENDED:
            gesture_label, target_cc, target_insert = "Middle+Ring: Insert 4", INSERT_4_CC, 4
        elif index_state == FingerState.EXTENDED and middle_state == FingerState.EXTENDED and ring_state == FingerState.CURLED and pinky_state == FingerState.CURLED:
            gesture_label, target_cc, target_insert = "Ring+Pinky: Insert 5", INSERT_5_CC, 5
        elif thumb_state == FingerState.CURLED and index_state == FingerState.EXTENDED and middle_state == FingerState.EXTENDED and ring_state == FingerState.EXTENDED and pinky_state == FingerState.EXTENDED:
            gesture_label = "Toggle: RECORD"
            target_cc = ARM_BASE_CC + midi_handler.active_insert

        if gesture_label != "No Toggle Detected." and gesture_label != previous_gesture:
            if target_insert:
                midi_handler.set_active_insert(target_insert)
            midi_handler.send_toggle(cc_number=target_cc, state=True)
            previous_gesture = gesture_label

    else:
        mid_straight = dist_middle > THRESHOLD_extended
        rng_straight = dist_ring > THRESHOLD_extended
        pky_straight = dist_pinky > THRESHOLD_extended
        
        # lock condition (mid ring pinky straight)
        automation_locked = mid_straight and rng_straight and pky_straight

        thumb_pos = (int(thumb_tip.x * width), int(thumb_tip.y * height))
        index_pos = (int(index_tip.x * width), int(index_tip.y * height))

        if not automation_locked:
            cv2.line(frame, thumb_pos, index_pos, PINK, 2)

            thumb_to_index_dist = calculate_distance(thumb_tip, index_tip)
            
            raw_perc = min(125, max(0, ((thumb_to_index_dist - 0.02) / (0.28 - 0.02)) * 125))
            
            if raw_perc < 5: 
                raw_perc = 0
                
            automation_smoothed += (raw_perc - automation_smoothed) * SMOOTHING_FACTOR
            
            # Send MIDI only when NOT locked
            midi_handler.send_automation(automation_smoothed, AUTOMATION_CC)
            gesture_label = f"Volume: {automation_smoothed:.0f}%"
        
        else:
            cv2.line(frame, thumb_pos, index_pos, (255, 255, 0), 1) # Cyan line for lock
            gesture_label = f"LOCKED: {automation_smoothed:.0f}%"

    return gesture_label