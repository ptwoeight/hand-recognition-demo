import cv2
import mediapipe as mp
from midi_out import MidiManager
import arm_mode
import mute_mode

class AppState:
    def __init__(self):
        self.current_mode = "ARM"
        self.is_running = True

state = AppState()

def start_vision():
    video_capture = cv2.VideoCapture(0)
    midi_handler = MidiManager('TestingFLPLSOMG')
    
    mp_hands = mp.solutions.hands
    hand_tracker = mp_hands.Hands(static_image_mode=False, max_num_hands=2)
    mp_draw = mp.solutions.drawing_utils
    
    PINK = (120, 29, 222)

    while state.is_running:
        success, frame = video_capture.read()
        if not success: break

        frame = cv2.flip(frame, 1)
        height, width, _ = frame.shape
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = hand_tracker.process(rgb_frame)

        gesture_label = "Scanning..."

        if results.multi_hand_landmarks:
            for hand_idx, hand_landmarks in enumerate(results.multi_hand_landmarks):
                hand_handedness = results.multi_handedness[hand_idx].classification[0].label
                
                # Pass 'frame' here so the engines can draw on it
                if state.current_mode == "MUTE":
                    gesture_label = arm_mode.process_logic(
                        hand_landmarks, hand_handedness, midi_handler, 
                        width, height, mp_hands, frame
                    )
                else:
                    gesture_label = mute_mode.process_logic(
                        hand_landmarks, hand_handedness, midi_handler, 
                        width, height, mp_hands, frame
                    )

                mp_draw.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)
                
                cv2.putText(frame, f"MODE: {state.current_mode} | {gesture_label}", (50, 50), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, PINK, 2)

        cv2.imshow("FL Gesture Controller", frame)
        if cv2.waitKey(1) & 0xFF == 27: 
            state.is_running = False

    video_capture.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    start_vision()