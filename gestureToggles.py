import cv2
import mediapipe as mp
import math
from enum import Enum
from midi_out import MidiManager

YELLOW = (0, 255, 255)

# Move Point class outside the loop to prevent re-defining it 30 times a second
class Point:
    def __init__(self, x, y):
        self.x = x
        self.y = y

def calculate_distance(point1, point2):     # euclidian type shi
    distance = math.sqrt((point2.x - point1.x)**2 + (point2.y - point1.y)**2)
    return distance

class FingerState(Enum):
    UNKNOWN = 0
    EXTENDED = 1
    CURLED = 2

# ↓↓ my finger thresholds ↓↓
THRESHOLD_extended = 0.12
THRESHOLD_curled = 0.03
THRESHOLD_thumb_curl = 0.02    # max dist for thumb tip to index MCP when curled
THRESHOLD_thumb_y_extend = 0.09     # for thumb out (y-axis extendsion threshold)

# ↓↓ set up mediapipe
mp_hands = mp.solutions.hands
hand_tracker = mp_hands.Hands(static_image_mode=False, max_num_hands=2)  # allow both hands
mp_draw = mp.solutions.drawing_utils

video_capture = cv2.VideoCapture(0)     # webcam opens in a window
previous_gesture = ""  # track the previous gesture to only print on change
recording_active = False  # track recording state for right hand toggle
previous_pinch_state = False  # track previous pinch state for toggle detection

# --- NEW IMPROVEMENTS VARIABLES ---
automation_smoothed = 0.0  # For smoothing the automation percentage
smoothing_factor = 0.2     # Lower = smoother/slower, Higher = snappier
gesture_debounce_counter = 0
DEBOUNCE_THRESHOLD = 3     # Must hold gesture for 3 frames
# ----------------------------------

midi_handler = MidiManager('Gesture Port')

while True:     # "loop through every frame until ESC is pressed"
    success, frame = video_capture.read()
    if not success: 
        break

    frame = cv2.flip(frame, 1)  # makes the cam mirrored
    height, width, _ = frame.shape

    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)  # rgb for mediapipe
    results = hand_tracker.process(rgb_frame)   # draw it baddie

    if results.multi_hand_landmarks:
        for hand_idx, hand_landmarks in enumerate(results.multi_hand_landmarks):
            hand_handedness = results.multi_handedness[hand_idx].classification[0].label  # "Left" or "Right"

            # --- NORMALIZATION IMPROVEMENT ---
            # Use distance between wrist and middle finger base to scale thresholds
            wrist = hand_landmarks.landmark[mp_hands.HandLandmark.WRIST]
            mcp_9 = hand_landmarks.landmark[mp_hands.HandLandmark.MIDDLE_FINGER_MCP]
            hand_scale = calculate_distance(wrist, mcp_9)
            if hand_scale == 0: hand_scale = 0.1 # prevent div by zero
            # ---------------------------------

            # ↓↓ the actual hand landmarks drawn ↓↓
            mp_draw.draw_landmarks(
                frame,
                hand_landmarks,
                mp_hands.HAND_CONNECTIONS,
                mp_draw.DrawingSpec(color=YELLOW, thickness=1, circle_radius=3),
                mp_draw.DrawingSpec(color=YELLOW, thickness=1),
            )

            # ↓↓ drawing the bounding box - LEFT HAND ONLY ↓↓
            landmark_positions = []     # need this to acc draw it
            for lm in hand_landmarks.landmark:
                x, y = int(lm.x * width), int(lm.y * height)
                landmark_positions.append((x, y))

            x_vals = [pt[0] for pt in landmark_positions]
            y_vals = [pt[1] for pt in landmark_positions]
            x_min, x_max = min(x_vals), max(x_vals)
            y_min, y_max = min(y_vals), max(y_vals)
            
            if hand_handedness == "Left":
                cv2.rectangle(frame, (x_min, y_min), (x_max, y_max), YELLOW, 2)   # draw it!

            # ↓↓ make the landmark coords as objs so they're accessible for gesture recog
            thumb_tip = hand_landmarks.landmark[mp_hands.HandLandmark.THUMB_TIP]
            thumb_mcp = hand_landmarks.landmark[mp_hands.HandLandmark.THUMB_MCP]    # lm 2 - base joint

            index_tip = hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_TIP]
            index_mcp = hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_MCP]    # lm 5 - base joint

            middle_tip = hand_landmarks.landmark[mp_hands.HandLandmark.MIDDLE_FINGER_TIP]
            middle_mcp = hand_landmarks.landmark[mp_hands.HandLandmark.MIDDLE_FINGER_MCP]    # lm 9 - base joint

            ring_tip = hand_landmarks.landmark[mp_hands.HandLandmark.RING_FINGER_TIP]
            ring_mcp = hand_landmarks.landmark[mp_hands.HandLandmark.RING_FINGER_MCP]    # lm 13 - base joint

            pinky_tip = hand_landmarks.landmark[mp_hands.HandLandmark.PINKY_TIP]
            pinky_mcp = hand_landmarks.landmark[mp_hands.HandLandmark.PINKY_MCP]    # lm 17 - base joint

            # ↓↓ distances for finger extension/curl ↓↓
            dist_thumb = calculate_distance(thumb_tip, thumb_mcp)
            dist_index = calculate_distance(index_tip, index_mcp)
            dist_middle = calculate_distance(middle_tip, middle_mcp)
            dist_ring = calculate_distance(ring_tip, ring_mcp)
            dist_pinky = calculate_distance(pinky_tip, pinky_mcp)

            # ↓↓ thumb curl checkers coz its weird ↓↓
            thumb_x_diff = thumb_tip.x - index_mcp.x  # positive if thumb tip is to the right of index MCP
            if hand_handedness == "Right":  # flip comparison for right hand
                thumb_x_diff = -thumb_x_diff
            thumb_y_diff = thumb_mcp.y - thumb_tip.y # positive if tip is above MCP, negative if below

            # ↓↓ defining finger states (Enum from before, yes u wrote that) ↓↓

            # ↓↓ thumbs: "check if its curled, if nah, check if it's extended"
            if thumb_x_diff < THRESHOLD_thumb_curl:
                thumb_state = FingerState.CURLED
            elif thumb_y_diff > THRESHOLD_thumb_y_extend:
                thumb_state = FingerState.EXTENDED
            else:
                thumb_state = FingerState.UNKNOWN # if it's neither clearly curled nor clearly extended.
                                                # helps avoid flickering between states.

            # ↓↓ define finger states here - they work well like dis idk 
            index_state = FingerState.EXTENDED if dist_index > THRESHOLD_extended else FingerState.CURLED
            middle_state = FingerState.EXTENDED if dist_middle > THRESHOLD_extended else FingerState.CURLED
            ring_state = FingerState.EXTENDED if dist_ring > THRESHOLD_extended else FingerState.CURLED
            pinky_state = FingerState.EXTENDED if dist_pinky > THRESHOLD_extended else FingerState.CURLED

            # ↓↓ detecting the fingers! ↓↓
            gesture_label = ""

            # idk whats the best for automaticity
            # best so far is: index, MIDDLE, middle+ring, ring+pinky OR index, INDEX+MIDDLE, middle+ring, ring+pinky
            # rn its index, middle, ring, middle+ring, ring+pinky
            """
             ★ PAAAAAT OVER HERE!!!! : cc_number for inserts and what not are STILL MAGIC NUMBERS, change them when functional
            """

            if hand_handedness == "Left":
                # ↓↓ LEFT HAND: TOGGLE SYSTEM ↓↓
                if (index_state == FingerState.CURLED and
                    middle_state == FingerState.EXTENDED and
                    ring_state == FingerState.EXTENDED and
                    pinky_state == FingerState.EXTENDED):
                    gesture_label = "Index: Insert 1"
                    if gesture_label != previous_gesture:
                        midi_handler.set_active_insert(1)
                        midi_handler.send_toggle(cc_number=21, state=True)  # ★
                        print("TOGGLE: Insert 1")
                        previous_gesture = gesture_label
                elif (index_state == FingerState.EXTENDED and
                    middle_state == FingerState.CURLED and
                    ring_state == FingerState.EXTENDED and
                    pinky_state == FingerState.EXTENDED):
                    gesture_label = "Middle: Insert 2"
                    if gesture_label != previous_gesture:
                        midi_handler.set_active_insert(2)
                        midi_handler.send_toggle(cc_number=22, state=True)  # ★
                        print("TOGGLE: Insert 2")
                        previous_gesture = gesture_label
                elif (index_state == FingerState.EXTENDED and
                    middle_state == FingerState.EXTENDED and
                    ring_state == FingerState.CURLED and
                    pinky_state == FingerState.EXTENDED):     #idk if the extend check is necessary
                    gesture_label = "Ring: Insert 3"
                    if gesture_label != previous_gesture:
                        midi_handler.set_active_insert(3)
                        midi_handler.send_toggle(cc_number=23, state=True)  # ★
                        print("TOGGLE: Insert 3")
                        previous_gesture = gesture_label
                elif (index_state == FingerState.EXTENDED and
                    middle_state == FingerState.CURLED and
                    ring_state == FingerState.CURLED and
                    pinky_state == FingerState.EXTENDED):
                    gesture_label = "Middle+Ring: Insert 4"
                    if gesture_label != previous_gesture:
                        midi_handler.set_active_insert(4)
                        midi_handler.send_toggle(cc_number=24, state=True)  # ★
                        print("TOGGLE: Insert 4")
                        previous_gesture = gesture_label
                elif (index_state == FingerState.EXTENDED and
                    middle_state == FingerState.EXTENDED and
                    ring_state == FingerState.CURLED and
                    pinky_state == FingerState.CURLED):
                    gesture_label = "Ring+Pinky: Insert 5"
                    if gesture_label != previous_gesture:
                        midi_handler.set_active_insert(5)
                        midi_handler.send_toggle(cc_number=25, state=True)  # ★
                        print("TOGGLE: Insert 5")
                        previous_gesture = gesture_label
                elif (thumb_state == FingerState.CURLED and
                    index_state == FingerState.EXTENDED and
                    middle_state == FingerState.EXTENDED and
                    ring_state == FingerState.EXTENDED and
                    pinky_state == FingerState.EXTENDED):
                    gesture_label = "Toggle: RECORD"
                    if gesture_label != previous_gesture:
                        # MAP: Insert 1 Record = CC 31, Insert 2 Record = CC 32, etc.
                        record_cc = 30 + midi_handler.active_insert 
                        midi_handler.send_toggle(cc_number=record_cc, state=True)
                        print(f"ARMING: Insert {midi_handler.active_insert}")
                        previous_gesture = gesture_label
                else:
                    gesture_label = "No Toggle Detected."
                    previous_gesture = gesture_label

            else:
                # ↓↓ RIGHT HAND: AUTOMATION CONTROL ↓↓
                # Check if middle and ring tips are together
                middle_ring_distance = calculate_distance(middle_tip, ring_tip)
                middle_ring_threshold = 0.05  # threshold for fingers being "together"
                fingers_together = middle_ring_distance < middle_ring_threshold
                
                # Calculate midpoint between middle and ring tips
                midpoint_x = (middle_tip.x + ring_tip.x) / 2
                midpoint_y = (middle_tip.y + ring_tip.y) / 2
                
                midpoint = Point(midpoint_x, midpoint_y)
                
                # Calculate distance between thumb and midpoint (automation percentage)
                thumb_to_midpoint = calculate_distance(thumb_tip, midpoint)
                
                # Define min and max distance for percentage calculation
                min_distance = 0.02  # when fingers are touching = 0%
                max_distance = 0.35  # when fully extended = 100%
                
                # Calculate percentage (mapped from min_distance to max_distance)
                if fingers_together:
                    raw_percentage = min(100, max(0, ((thumb_to_midpoint - min_distance) / (max_distance - min_distance)) * 100))
                    # LERP smoothing: value = old + (new - old) * factor
                    automation_smoothed += (raw_percentage - automation_smoothed) * smoothing_factor
                    automation_percentage = automation_smoothed

                    midi_handler.send_automation(automation_percentage)
                else:
                    automation_percentage = 0  # reset to 0 if fingers aren't together
                    automation_smoothed = 0 # reset smoothing
                
                # Calculate distance between thumb and index (record toggle)
                thumb_to_index = calculate_distance(thumb_tip, index_tip)
                record_toggle_threshold = 0.05
                is_pinched = thumb_to_index < record_toggle_threshold
                
                # Toggle recording state only on transition from not pinched to pinched
                if is_pinched and not previous_pinch_state:
                    recording_active = not recording_active
                    if recording_active:
                        print("RECORDING: ON")
                    else:
                        print("RECORDING: OFF")
                previous_pinch_state = is_pinched
                
                # Only draw automation line if middle and ring are together
                if fingers_together:
                    # Draw line between thumb and midpoint
                    thumb_pos = (int(thumb_tip.x * width), int(thumb_tip.y * height))
                    midpoint_pos = (int(midpoint.x * width), int(midpoint.y * height))
                    line_color = (0, 255, 0) if recording_active else YELLOW  # Green if recording, yellow if not
                    cv2.line(frame, thumb_pos, midpoint_pos, line_color, 1)
                    
                    # Draw circles at endpoints
                    cv2.circle(frame, thumb_pos, 5, line_color, -1)
                    cv2.circle(frame, midpoint_pos, 5, line_color, -1)
                    
                    # Display automation percentage
                    gesture_label = f"Automation: {automation_percentage:.0f}%"
                    if recording_active:
                        gesture_label += " [RECORDING]"
                else:
                    gesture_label = "Position middle + ring together"

            cv2.putText(frame, gesture_label, (x_min, y_min - 10), cv2. FONT_HERSHEY_SIMPLEX, 1, YELLOW, 2)

    cv2.imshow("Gesture Toggle Test", frame)
    if cv2.waitKey(1) & 0xFF == 27:    # esc to quit
        break
        
# cleanup baso
video_capture.release()
cv2.destroyAllWindows()