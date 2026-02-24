import mido

class MidiManager:
    def __init__(self, port_name='Gesture Port'):
        self.port_name = port_name
        try:
            self.output = mido.open_output(self.port_name)  # open the virtual port from loopmidi
            print(f"SUCCESS: Connected to {self.port_name}")
        except IOError:
            print(f"ERROR: Could not connect to {self.port_name}. Check loopMIDI.")
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


