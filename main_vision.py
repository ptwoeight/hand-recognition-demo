import os
import eel
import cv2
import mediapipe as mp
from midi_out import MidiManager
import arm_mode
import mute_mode
import calibration_mode
from pygrabber.dshow_graph import FilterGraph
import psutil
# import rtmidi

# Forces Python to look in the folder where the script lives
os.chdir(os.path.dirname(os.path.abspath(__file__)))

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
        
        # colour stuff
        self.hud_color = (120, 29, 222) # Default
        self.landmark_color = (120, 29, 222) # Default

state = AppState()

# [2] EEL EXPOSED FUNCTIONS
@eel.expose
def update_colors(hex_color):
    # Convert Hex (#DE1D5D) to BGR for OpenCV (120, 29, 222)
    hex_color = hex_color.lstrip('#')
    rgb = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    bgr = (rgb[2], rgb[1], rgb[0])
    
    state.hud_color = bgr
    state.landmark_color = bgr
    print(f"UI Colors updated to BGR: {bgr}")

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
    print("-----------------")
    print("Closing Application. BYE BYE!")
    print("-----------------")


# [3] MAIN VISION LOOP
def start_vision():
    state.cap = cv2.VideoCapture(state.camera_index)
    midi_handler = MidiManager('TestingFLPLSOMG')
    
    # Setup MediaPipe
    mp_hands = mp.solutions.hands
    hand_tracker = mp_hands.Hands(static_image_mode=False, max_num_hands=2)
    mp_draw = mp.solutions.drawing_utils

    selected_browser = 'firefox' # Default if config fails
    try:
        if os.path.exists(".browser_cfg"):
            with open(".browser_cfg", "r") as f:
                selected_browser = f.read().strip()
    except Exception as e:
        print(f"Browser config error: {e}")


    # Get the directory where main_vision.py is located
    base_path = os.path.dirname(os.path.abspath(__file__))

    # Change the current working directory to that folder
    os.chdir(base_path)

    # Initialising Eel
    eel.init('web')
    # Using 'block=False' allows the Python loop to run alongside the UI
    eel.start('index.html', mode=selected_browser, block=False)


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
                full_text = f"[{hand_handedness.upper()}] {gesture_label}"
                font = cv2.FONT_HERSHEY_SIMPLEX
                font_scale = 0.6
                thickness = 2
                (text_w, text_h), baseline = cv2.getTextSize(full_text, font, font_scale, thickness)

                # Set Margin from edges (decreased to 20px for "closer to edge")
                margin = 20 
                WHITE = (255, 255, 255)
                DARK_GREY = (40, 40, 40)
                
                if hand_handedness == "Left":
                    text_x, text_y = margin, (margin * 2)
                    bg_color = DARK_GREY # dark grey
                    text_color = WHITE
                else:
                    text_x, text_y = width - text_w - margin, (margin * 2)
                    bg_color = DARK_GREY
                    text_color = state.hud_color

                # [3] DRAW SEMI-TRANSPARENT BACKGROUND
                # Create an overlay layer for the transparency effect
                overlay = frame.copy()
                # Draw the rectangle box (slightly larger than the text)
                cv2.rectangle(overlay, (text_x - 10, text_y - 25), (text_x + text_w + 10, text_y + 10), bg_color, -1)
                
                # Blend the overlay with the original frame (0.6 = 60% opacity)
                alpha = 0.6
                cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0, frame)

                # [4] DRAW TEXT ON TOP
                cv2.putText(frame, full_text, (text_x, text_y), font, font_scale, text_color, thickness)
                mp_draw.draw_landmarks(
                    frame, 
                    hand_landmarks, 
                    mp_hands.HAND_CONNECTIONS, 
                    mp_draw.DrawingSpec(color=state.hud_color, thickness=1, circle_radius=3), 
                    mp_draw.DrawingSpec(color=WHITE, thickness=1)
                )

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