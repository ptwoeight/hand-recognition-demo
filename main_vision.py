import eel
import cv2
import mediapipe as mp
from midi_out import MidiManager
import arm_mode
import mute_mode

# [1] STATE CONTROLLER
class AppState:
    def __init__(self):
        self.current_mode = "ARM"
        self.is_running = True

state = AppState()

# [2] EEL EXPOSED FUNCTIONS
@eel.expose
def change_mode(new_mode):
    state.current_mode = new_mode
    print(f"[UI Switch] Current Mode: {new_mode}")

@eel.expose
def stop_application():
    state.is_running = False
    print("Closing Application. BYE BYE!")

# [3] MAIN VISION LOOP
def start_vision():
    # Setup Camera & MIDI
    video_capture = cv2.VideoCapture(0)
    midi_handler = MidiManager('TestingFLPLSOMG')
    
    # Setup MediaPipe
    mp_hands = mp.solutions.hands
    hand_tracker = mp_hands.Hands(static_image_mode=False, max_num_hands=2)
    mp_draw = mp.solutions.drawing_utils
    
    # Colors
    PINK = (120, 29, 222)
    WHITE = (255, 255, 255)

    # Initialising Eel
    eel.init('web')
    # Using 'block=False' allows the Python loop to run alongside the UI
    eel.start('index.html', mode='firefox', block=False)

    while state.is_running:
        eel.sleep(0.01) # Keeps UI responsive

        success, frame = video_capture.read()
        if not success: break

        frame = cv2.flip(frame, 1)
        height, width, _ = frame.shape
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = hand_tracker.process(rgb_frame)

        if results.multi_hand_landmarks:
            for hand_idx, hand_landmarks in enumerate(results.multi_hand_landmarks):
                hand_handedness = results.multi_handedness[hand_idx].classification[0].label
                
                # [1] RUN LOGIC ENGINE
                if state.current_mode == "ARM":
                    gesture_label = arm_mode.process_logic(
                        hand_landmarks, hand_handedness, midi_handler, 
                        width, height, mp_hands, frame
                    )
                else:
                    gesture_label = mute_mode.process_logic(
                        hand_landmarks, hand_handedness, midi_handler, 
                        width, height, mp_hands, frame
                    )

                # [2] CALCULATE TEXT ALIGNMENT
                full_text = f"{hand_handedness}: {gesture_label}"
                font = cv2.FONT_HERSHEY_SIMPLEX
                font_scale = 0.7
                thickness = 2

                if hand_handedness == "Left":
                    # Standard Left Alignment
                    text_pos = (50, 50)
                    display_color = WHITE
                else:
                    # RIGHT ALIGNMENT MATH
                    # Get the width of the text string in pixels
                    (text_width, text_height), baseline = cv2.getTextSize(full_text, font, font_scale, thickness)
                    
                    # Anchor point is the right edge (width - 50px) minus the calculated text width
                    right_anchor = width - 50
                    text_pos = (right_anchor - text_width, 50)
                    display_color = PINK

                # [3] DRAW OVERLAYS
                cv2.putText(frame, full_text, text_pos, font, font_scale, display_color, thickness)
                mp_draw.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)

        # Show the processed frame
        cv2.imshow("FL Gesture Controller", frame)
        
        # ESC key safety exit
        if cv2.waitKey(1) & 0xFF == 27: 
            state.is_running = False

    # Cleanup
    video_capture.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    start_vision()