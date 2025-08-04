import cv2
import mediapipe as mp
import math

ORANGE = (0, 140, 255)   # opencv wants bgr format


def calculate_distance(point1, point2):
    # calculate the euclidean distance etween two points
    distance = math.sqrt((point2.x - point1.x)**2 + (point2.y - point1.y)**2)
    return distance

from enum import Enum
class FingerState(Enum):
    UNKNOWN = 0
    EXTENDED = 1
    CURLED = 2

# finger thresholds
THRESHOLD_EXTENDED = 0.12
THRESHOLD_CURLED = 0.04
THRESHOLD_PEACE_SPREAD = 0.07   # distance between index and middle finger tips
THRESHOLD_OK_PROXIMITY = 0.05   # distance between thumb and index finger tips
THRESHOLD_THUMB_OVERLAP_CURLED = 0.077   # max distance for thumb tip to index MCP when thumb is curled/overlapping
# Threshold for thumb Y-axis extension (for Thumb Out and Open Hand)
THRESHOLD_THUMB_Y_EXTENDED_DIFF = 0.090 # Placeholder: if (thumb_mcp.y - thumb_tip.y) > this, thumb is extended upwards

'''
these values are fixed for now because they're for MY hand. 
we'll make them calculations to make the thresholds proportional to a reference hand measurement within the same frame.
   e.g. (distance / distance from wrist to middle mcp) > some ratio idk

we can always add a user calibration feature where the user performs an 'open hand' and 'closed fist'
   >> record the user's specific ranges for EXTENDED and CURLED for their fingers to be used as personalised thresholds.)
'''

# mediapipe; set up hand tracking
mp_hands = mp.solutions.hands
hand_tracker = mp_hands.Hands(static_image_mode=False, max_num_hands=1)
mp_draw = mp.solutions.drawing_utils

# webcam opens in a window here
video_capture = cv2.VideoCapture(0)

while True:    # "loop through every frame until ESC is pressed"
    success, frame = video_capture.read()
    if not success:
        break

    frame = cv2.flip(frame, 1)
    height, width, _ = frame.shape

    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)   # mediapipe wants rgb format
    results = hand_tracker.process(rgb_frame)

    if results.multi_hand_landmarks:
        for hand_landmarks in results.multi_hand_landmarks:
            
            # hand landmarks drawn and connected here
            mp_draw.draw_landmarks(
                frame,
                hand_landmarks,
                mp_hands.HAND_CONNECTIONS,
                mp_draw.DrawingSpec(color=ORANGE, thickness=1, circle_radius=3),
                mp_draw.DrawingSpec(color=ORANGE, thickness=1),
            )

            # extract and store landmark coords
            landmark_positions = []
            for lm in hand_landmarks.landmark:
                x, y = int(lm.x * width), int(lm.y * height)
                landmark_positions.append((x, y))

            # bounding box around hand drawn here
            x_vals = [pt[0] for pt in landmark_positions]
            y_vals = [pt[1] for pt in landmark_positions]
            x_min, x_max = min(x_vals), max(x_vals)
            y_min, y_max = min(y_vals), max(y_vals)
            cv2.rectangle(frame, (x_min, y_min), (x_max, y_max), ORANGE, 2)

            # gesture recognition - access landmark objects instead of coordinates
            thumb_tip = hand_landmarks.landmark[mp_hands.HandLandmark.THUMB_TIP]
            thumb_mcp = hand_landmarks.landmark[mp_hands.HandLandmark.THUMB_MCP]    # lm 2

            index_tip = hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_TIP]
            index_mcp = hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_MCP]    # lm 5

            middle_tip = hand_landmarks.landmark[mp_hands.HandLandmark.MIDDLE_FINGER_TIP]
            middle_mcp = hand_landmarks.landmark[mp_hands.HandLandmark.MIDDLE_FINGER_MCP]    # lm 9

            ring_tip = hand_landmarks.landmark[mp_hands.HandLandmark.RING_FINGER_TIP]
            ring_mcp = hand_landmarks.landmark[mp_hands.HandLandmark.RING_FINGER_MCP]    # lm 13

            pinky_tip = hand_landmarks.landmark[mp_hands.HandLandmark.PINKY_TIP]
            pinky_mcp = hand_landmarks.landmark[mp_hands.HandLandmark.PINKY_MCP]    # lm 17

            # distances for finger extension/curl
            dist_thumb = calculate_distance(thumb_tip, thumb_mcp)
            dist_index = calculate_distance(index_tip, index_mcp)
            dist_middle = calculate_distance(middle_tip, middle_mcp)
            dist_ring = calculate_distance(ring_tip, ring_mcp)
            dist_pinky = calculate_distance(pinky_tip, pinky_mcp)

            # specific distances
            dist_index_middle_tips = calculate_distance(index_tip, middle_tip)  # peace sign (index and middle tip distance)
            dist_thumb_index_tips = calculate_distance(thumb_tip, index_tip)    # 'ok' sign (thumb and index tip distance)

            # This checks if the thumb tip is close to the index finger's MCP (base knuckle)
            # indicating it's curled across the palm.
            dist_thumb_tip_to_index_mcp = calculate_distance(thumb_tip, index_mcp)

            # --- NEW: Calculate the Y-difference for thumb extension ---
            thumb_y_diff = thumb_mcp.y - thumb_tip.y # Positive if tip is above MCP, negative if below

            # You can uncomment these lines when you're calibrating your thresholds.
            print(f"Dists: T:{dist_thumb:.3f} I:{dist_index:.3f} M:{dist_middle:.3f} R:{dist_ring:.3f} P:{dist_pinky:.3f}")
            # Update this print line to include the new Y-diff
            print(f"Special Dists: IM:{dist_index_middle_tips:.3f} TI:{dist_thumb_index_tips:.3f} T_IMCP:{dist_thumb_tip_to_index_mcp:.3f} T_Y_DIFF:{thumb_y_diff:.3f}")

            # determine finger states (enum)
            # Logic: First, check if it's curled (overlapping). If not, then check if it's extended upwards.
            if dist_thumb_tip_to_index_mcp < THRESHOLD_THUMB_OVERLAP_CURLED:
                thumb_state = FingerState.CURLED
            elif thumb_y_diff > THRESHOLD_THUMB_Y_EXTENDED_DIFF:
                thumb_state = FingerState.EXTENDED
            else:
                thumb_state = FingerState.UNKNOWN # If it's neither clearly curled nor clearly extended.
                                                # This helps avoid flickering between states.

            # Other finger states remain the same as they were working well
            index_state = FingerState.EXTENDED if dist_index > THRESHOLD_EXTENDED else FingerState.CURLED
            middle_state = FingerState.EXTENDED if dist_middle > THRESHOLD_EXTENDED else FingerState.CURLED
            ring_state = FingerState.EXTENDED if dist_ring > THRESHOLD_EXTENDED else FingerState.CURLED
            pinky_state = FingerState.EXTENDED if dist_pinky > THRESHOLD_EXTENDED else FingerState.CURLED
            
            # the aaactual gesture recognition logic lel
            gesture_label = ""

            # 1. OK Sign (Very specific: thumb-index proximity + 3 fingers extended)
            if (dist_thumb_index_tips < THRESHOLD_OK_PROXIMITY and
                middle_state == FingerState.EXTENDED and
                ring_state == FingerState.EXTENDED and
                pinky_state == FingerState.EXTENDED):
                gesture_label = "OK Sign"

            # 2. Peace Sign (Specific: 2 fingers extended + spread + others curled)
            elif (thumb_state == FingerState.CURLED and # Thumb needs to be curled for this
                index_state == FingerState.EXTENDED and
                middle_state == FingerState.EXTENDED and
                ring_state == FingerState.CURLED and
                pinky_state == FingerState.CURLED and
                dist_index_middle_tips > THRESHOLD_PEACE_SPREAD):
                gesture_label = "Peace Sign"

            # 3. Pointing (Specific: 1 finger extended + others curled)
            elif (thumb_state == FingerState.CURLED and # Thumb needs to be curled for this
                index_state == FingerState.EXTENDED and
                middle_state == FingerState.CURLED and
                ring_state == FingerState.CURLED and
                pinky_state == FingerState.CURLED):
                gesture_label = "Pointing"

            # 4. Closed Fist (All fingers curled, including the thumb with its new curled logic)
            elif (thumb_state == FingerState.CURLED and # Now uses the new overlapping thumb logic
                index_state == FingerState.CURLED and
                middle_state == FingerState.CURLED and
                ring_state == FingerState.CURLED and
                pinky_state == FingerState.CURLED):
                gesture_label = "Closed Fist"

            # 5. Thumb Out (Specific: Thumb extended + others curled - now less likely to conflict with fist)
            elif (thumb_state == FingerState.EXTENDED and # Thumb must be truly extended (not overlapping curled)
                index_state == FingerState.CURLED and
                middle_state == FingerState.CURLED and
                ring_state == FingerState.CURLED and
                pinky_state == FingerState.CURLED):
                gesture_label = "Thumb Out"

            # 6. Open Hand (Most general: All fingers extended - less likely to conflict with other extended finger gestures)
            elif (thumb_state == FingerState.EXTENDED and # Thumb must be truly extended
                index_state == FingerState.EXTENDED and
                middle_state == FingerState.EXTENDED and
                ring_state == FingerState.EXTENDED and
                pinky_state == FingerState.EXTENDED):
                gesture_label = "Open Hand"

            # 7. ROCK ONNN 
            elif (thumb_state == FingerState.EXTENDED and
                  index_state == FingerState.EXTENDED and
                  middle_state == FingerState.CURLED and
                  ring_state == FingerState.CURLED and
                  pinky_state == FingerState.EXTENDED):
                gesture_label = "ROCK ON XDDD"


            cv2.putText(frame, gesture_label, (x_min, y_min - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, ORANGE, 2)
        


    # show the frame w landmarks and gesture label
    cv2.imshow("GestureDemo", frame)
    if cv2.waitKey(1) & 0xFF == 27:    # esc to quit
        break

# cleanup baso
video_capture.release()
cv2.destroyAllWindows()
