import eel
import cv2
import mediapipe as mp
from midi_out import MidiManager
import arm_mode
import mute_mode
import calibration_mode
from pygrabber.dshow_graph import FilterGraph
import psutil
import rtmidi

# [1] STATE CONTROLLER
class AppState:
    def __init__(self):
        self.current_mode = "OFF"
        self.is_running = True
        self.active_insert = 1
        self.calibration_step = 0 # 0=not started 1=resting 2=stretched

        self.camera_index = 0
        self.cap = None

        # Calibration Defaults (gonna be updated)
        self.calib_extended = 0.12
        self.calib_curled = 0.03
        self.calib_thumb_curl = 0.02
        self.calib_thumb_y_extend = 0.09
        self.calib_max_stretch  = 0.28
        self.calib_smoothing_factor = 0.2
        

state = AppState()

# [2] EEL EXPOSED FUNCTIONS
@eel.expose
def check_midi_status():
    loopmidi_running = any("loopMIDI.exe" in p.name() for p in psutil.process_iter())
    
    if not loopmidi_running:
        print("[System Check] loopMIDI process not found.")
    
    return loopmidi_running

@eel.expose
def change_mode(new_state):
    state.current_mode = new_state
    print(f"State: {new_state}")

@eel.expose
def next_calibration_step():
    state.calibration_step += 1
    if state.calibration_step > 2:
        print("[Calibration] Finalized and Saved.")
    return state.calibration_step

@eel.expose
def get_camera_list():
    graph = FilterGraph()
    device_names = graph.get_input_devices()
    
    # create a list of objects so the UI knows both the Name and the Index
    camera_data = []
    for index, name in enumerate(device_names):
        camera_data.append({
            "index": index,
            "name": name
        })
    
    print(f"Detected Cameras: {camera_data}")
    return camera_data

@eel.expose
def set_camera_index(index):
    state.camera_index = int(index)
    # Re-initialize the capture with the new index
    if state.cap is not None:
        state.cap.release()
    state.cap = cv2.VideoCapture(state.camera_index)
    print(f"Camera successfully switched to index: {index}")

@eel.expose
def reset_calibration():
    state.calibration_step = 0
    state.current_mode = "OFF"
    print("[Calibration] Cancelled by user.")

@eel.expose
def stop_application():
    state.is_running = False
    print("Closing Application. BYE BYE!")

# [3] MAIN VISION LOOP
def start_vision():
    state.cap = cv2.VideoCapture(state.camera_index)
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

        # IDLE
        if state.current_mode == "OFF":
            # close window if theres one open
            if cv2.getWindowProperty("FL Gesture Controller", cv2.WND_PROP_VISIBLE) >= 1:
                cv2.destroyWindow("FL Gesture Controller")
            continue

        # CAMERA ACTIVE
        success, frame = state.cap.read()
        if not success: 
            # on camera start failure
            print("Camera not detected.")
            state.current_mode = "OFF"
            continue

        frame = cv2.flip(frame, 1)
        height, width, _ = frame.shape
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = hand_tracker.process(rgb_frame)

        if results.multi_hand_landmarks:
            for hand_idx, hand_landmarks in enumerate(results.multi_hand_landmarks):
                hand_handedness = results.multi_handedness[hand_idx].classification[0].label
                gesture_label = ""

                # [1] RUN LOGIC ENGINE
                if state.current_mode == "ARM":
                    gesture_label = arm_mode.process_logic(
                        hand_landmarks, hand_handedness, midi_handler, 
                        width, height, mp_hands, frame, state
                    )
                elif state.current_mode == "MUTE":
                    gesture_label = mute_mode.process_logic(
                        hand_landmarks, hand_handedness, midi_handler, 
                        width, height, mp_hands, frame, state
                    )
                elif state.current_mode == "CALIBRATE":
                    gesture_label = calibration_mode.process_calibration(
                        hand_landmarks, state, mp_hands
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
    if state.cap:
        state.cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    start_vision()