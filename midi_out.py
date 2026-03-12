import os
import mido

# FORCE Python to look at the correct backend binaries
try:
    mido.set_backend('mido.backends.rtmidi')
except Exception as e:
    print(f"Manual Load Failed: {e}")

class MidiManager:
    """ def __init__(self, port_name='Gesture Port'):
        self.port_name = port_name
        try:
            self.output = mido.open_output(self.port_name)  # open the virtual port from loopmidi
            print(f"SUCCESS: Connected to {self.port_name}")
        except IOError:
            print(f"ERROR: Could not connect to {self.port_name}. Check loopMIDI.")
            self.output = None """

    def __init__(self, port_name='Gesture Port'):
        self.port_name = port_name
        self.active_insert = 1  # Initialize this so it doesn't crash later
        try:
            self.output = mido.open_output(self.port_name)
            print(f"SUCCESS: Connected to {self.port_name}")
        except Exception as e:
            # Instead of crashing, we just set output to None
            print(f"MIDI WARNING: Could not connect to {self.port_name}. (Error: {e})")
            print("Running in 'Camera Only' mode.")
            self.output = None

    def set_active_insert(self, insert_number):
        self.active_insert = insert_number

    def send_automation(self, percentage, cc_number=20):
        if self.output: 
            midi_value = int((percentage / 100) * 127)  # Scale 0-100 to 0-127
            midi_value = max(0, min(127, midi_value))   # Clip values just in case

            # CC Message
            msg = mido.Message('control_change', control=cc_number, value=midi_value)
            self.output.send(msg)

    def send_toggle(self, cc_number, state):
        if self.output:     # sends 127: ON, 0: OFF for toggle
            value = 127 if state else 0
            msg = mido.Message('control_change', control=cc_number, value=value)
            self.output.send(msg)


