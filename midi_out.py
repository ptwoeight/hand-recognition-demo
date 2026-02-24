import mido

class MidiManager:
    def __init__(self, port_name='Gesture Port'):
        self.port_name = port_name
        try:
            # open the virtual port from loopmidi
            self.output = mido.open_output(self.port_name)
            print(f"SUCCESS: Connected to {self.port_name}")
        except IOError:
            print(f"ERROR: Could not connect to {self.port_name}. Check loopMIDI.")
            self.output = None

    def send_automation(self, percentage, cc_number=20):
        if self.output: 
            # Scale 0-100 to 0-127
            midi_value = int((percentage / 100) * 127)
            # Clip values just in case
            midi_value = max(0, min(127, midi_value))

            # CC Message
            msg = mido.Message('control_change', control=cc_number, value=midi_value)
            self.output.send(msg)