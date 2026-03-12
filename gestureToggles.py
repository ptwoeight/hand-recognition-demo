import cv2
import mediapipe as mp
import math
from enum import Enum
from midi_out import MidiManager

# == [1] CONFIGS + CONSTANTS == #

# midi cc values: using undefined 20-31
INSERT_1_CC = 21
INSERT_2_CC = 22
INSERT_3_CC = 23
INSERT_4_CC = 24
INSERT_5_CC = 25
ARM_BASE_CC = 30  # final cc = 30 + active_insert
AUTOMATION_CC = 20

# tracking + thresholds (mine)
YELLOW = (0, 255, 255)
THRESHOLD_extended = 0.12
THRESHOLD_curled = 0.03
THRESHOLD_thumb_curl = 0.02    # max dist for thumb tip to index MCP when curled
THRESHOLD_thumb_y_extend = 0.09     # for thumb out (y-axis extendsion threshold)
SMOOTHING_FACTOR = 0.2     # lower = smoother/slower, higher = snappier

class FingerState(Enum):
    UNKNOWN = 0
    EXTENDED = 1
    CURLED = 2

class Point:
    def __init__(self, x, y):
        self.x = x
        self.y = y

def calculate_distance(point1, point2):     # euclidian type shi
    distance = math.sqrt((point2.x - point1.x)**2 + (point2.y - point1.y)**2)
    return distance

# == [2] INITIALISING HARDWARE (in order)== #
video_capture = cv2.VideoCapture(0)   # webcam init
if not video_capture.isOpened():
    print("FATAL ERROR: System cannot access webcam.")
    exit()

midi_handler = MidiManager('FLGesture')   # MIDI init - ensures a busy MIDI port doesn't crash cam window

# --- TERMINAL CONNECTION CHECK ---
if midi_handler.output is not None:
    print("----------------------------------------------")
    print("✅ SUCCESS: MIDI Bridge 'FLGesture' is ACTIVE")
    print("Status: Handshakes with FL Studio are ready.")
    print("----------------------------------------------")
else:
    print("----------------------------------------------")
    print("⚠️  WARNING: MIDI Bridge NOT FOUND")
    print("Status: Camera will work, but no MIDI will be sent.")
    print("Action: Ensure loopMIDI is running and port is named correctly.")
    print("----------------------------------------------")

# set up mediapipe
mp_hands = mp.solutions.hands
hand_tracker = mp_hands.Hands(static_image_mode=False, max_num_hands=2)  # allow both hands
mp_draw = mp.solutions.drawing_utils

# == [3] GLOBAL STATE VARIABLES == #
previous_gesture = ""
automation_smoothed = 0.0
previous_pinch_state = False
recording_active = False

# ---------- MAIN ---------- #
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

                # helper variables for keeping code nice and clean
                current_gesture_type = None
                target_cc = None
                target_insert = None

                # insert 1
                if (index_state == FingerState.CURLED and
                    middle_state == FingerState.EXTENDED and
                    ring_state == FingerState.EXTENDED and
                    pinky_state == FingerState.EXTENDED):
                    gesture_label = "Index: Insert 1"
                    target_cc = INSERT_1_CC
                    target_insert = 1

                # insert 2
                elif (index_state == FingerState.EXTENDED and
                    middle_state == FingerState.CURLED and
                    ring_state == FingerState.EXTENDED and
                    pinky_state == FingerState.EXTENDED):
                    gesture_label = "Middle: Insert 2"
                    target_cc = INSERT_2_CC
                    target_insert = 2

                # insert 3
                elif (index_state == FingerState.EXTENDED and
                    middle_state == FingerState.EXTENDED and
                    ring_state == FingerState.CURLED and
                    pinky_state == FingerState.EXTENDED):     #idk if the extend check is necessary
                    gesture_label = "Ring: Insert 3"
                    target_cc = INSERT_3_CC
                    target_insert = 3

                # insert 4
                elif (index_state == FingerState.EXTENDED and
                    middle_state == FingerState.CURLED and
                    ring_state == FingerState.CURLED and
                    pinky_state == FingerState.EXTENDED):
                    gesture_label = "Middle+Ring: Insert 4"
                    target_cc = INSERT_4_CC
                    target_insert = 4

                # insert 5
                elif (index_state == FingerState.EXTENDED and
                    middle_state == FingerState.EXTENDED and
                    ring_state == FingerState.CURLED and
                    pinky_state == FingerState.CURLED):
                    gesture_label = "Ring+Pinky: Insert 5"
                    target_cc = INSERT_5_CC
                    target_insert = 5

                # record arming
                elif (thumb_state == FingerState.CURLED and
                    index_state == FingerState.EXTENDED and
                    middle_state == FingerState.EXTENDED and
                    ring_state == FingerState.EXTENDED and
                    pinky_state == FingerState.EXTENDED):
                    gesture_label = "Toggle: RECORD"
                    # uses the base (30) + the last touched insert
                    target_cc = ARM_BASE_CC + midi_handler.active_insert
                else:
                    gesture_label = "No Toggle Detected."

                # debouncing: only send midi if the gesture just changed
                if gesture_label != "No Toggle Detected." and gesture_label != previous_gesture:
                    if target_insert:
                        midi_handler.set_active_insert(target_insert)
                    
                    # sends midi signal through midimanager
                    midi_handler.send_toggle(cc_number=target_cc, state=True)
                    print(f"MIDI SENT: {gesture_label} on CC {target_cc}")

                previous_gesture = gesture_label

            else:
                # ↓↓ RIGHT HAND: AUTOMATION CONTROL ↓↓
                
                # automation mode (middle+ring tips together)
                middle_ring_distance = calculate_distance(middle_tip, ring_tip)
                middle_ring_threshold = 0.05 
                automation_mode_active = middle_ring_distance < middle_ring_threshold
                
                # automation slider (vert distance)
                if automation_mode_active:
                    # calculate midpoint between two fingers (stable tracking point)
                    midpoint_x = (middle_tip.x + ring_tip.x) / 2
                    midpoint_y = (middle_tip.y + ring_tip.y) / 2
                    midpoint = Point(midpoint_x, midpoint_y)
                    
                    thumb_to_midpoint = calculate_distance(thumb_tip, midpoint)     # distance from thumb to midpoint
                    
                    # mapping logic: min (0.02) to max (0.35) distance -> 0 to 100%
                    min_dist, max_dist = 0.02, 0.35
                    raw_percentage = min(100, max(0, ((thumb_to_midpoint - min_dist) / (max_dist - min_dist)) * 100))
                    
                    if raw_percentage < 5: raw_percentage = 0   # snap to zero if hand is super close for stability
                    automation_smoothed += (raw_percentage - automation_smoothed) * SMOOTHING_FACTOR    # smoothing (LERP) to prevent "jittery" midi knobs in fl
                    
                    # send midi 
                    midi_handler.send_automation(automation_smoothed, AUTOMATION_CC)
                    gesture_label = f"Auto: {automation_smoothed:.0f}%"
                else:
                    # reset smoothing when hand is relaxed to avoid "jumping" values
                    automation_smoothed = 0
                    gesture_label = "Touch Middle + Ring"

                # record automation toggle (index curled)
                is_index_curled = (index_state == FingerState.CURLED)
                
                if is_index_curled and not previous_pinch_state:
                    recording_active = not recording_active
                    
                    # send toggle cc
                    target_arm_cc = ARM_BASE_CC + midi_handler.active_insert
                    midi_handler.send_toggle(cc_number=target_arm_cc, state=recording_active)
                    print(f"RECORDING STATE: {'ON' if recording_active else 'OFF'}")
                
                # save state for next frame
                previous_pinch_state = is_index_curled 

                # visual feedback for automation mode + arm state
                if automation_mode_active:
                    thumb_pos = (int(thumb_tip.x * width), int(thumb_tip.y * height))
                    midpoint_pos = (int(midpoint.x * width), int(midpoint.y * height))
                    
                    line_color = (0, 255, 0) if recording_active else YELLOW
                    cv2.line(frame, thumb_pos, midpoint_pos, line_color, 2)
                    
                    if recording_active:
                        gesture_label += " [ARMED]"

            cv2.putText(frame, gesture_label, (x_min, y_min - 10), cv2. FONT_HERSHEY_SIMPLEX, 1, YELLOW, 2)

    cv2.imshow("Gesture Toggle Test", frame)
    if cv2.waitKey(1) & 0xFF == 27:    # esc to quit
        break
    
        
# cleanup baso
video_capture.release()
cv2.destroyAllWindows()