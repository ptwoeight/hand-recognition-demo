import mido
import os

# Force Python to use Pygame as the MIDI engine
try:
    os.environ['MIDO_BACKEND'] = 'mido.backends.pygame'
    import pygame.midi
    pygame.midi.init()
    print("[SUCCESS] Switched to Pygame MIDI backend.")
except Exception as e:
    print(f"[ERROR] Pygame fallback failed: {e}")

class MidiManager:
    def __init__(self, port_substring='FLGesture'):
        self.port_name = port_substring
        self.output = None
        self.active_insert = 1 # Default track
        
        try:
            import pygame.midi
            pygame.midi.init()
            
            all_ports = mido.get_output_names()
            matches = [p for p in all_ports if self.port_name in p]
            
            if matches:
                actual_name = matches[0]
                self.output = mido.open_output(actual_name)
                print(f"[SUCCESS] Connected to {actual_name}")
            else:
                print(f"[WARNING] No port found containing '{self.port_name}'")
        except Exception as e:
            print(f"[MIDI INIT ERROR] {e}")

    def set_active_insert(self, insert_number):
        """Updates which mixer track is targeted by the 'Arm' gesture."""
        self.active_insert = insert_number
        print(f"Targeting Mixer Insert: {self.active_insert}")

    def send_automation(self, percentage, cc_number=20):
        if self.output: 
            midi_value = int((percentage / 100) * 127)
            midi_value = max(0, min(127, midi_value))
            msg = mido.Message('control_change', control=cc_number, value=midi_value)
            self.output.send(msg)

    def send_toggle(self, cc_number, state):
        if self.output:
            value = 127 if state else 0
            msg = mido.Message('control_change', control=cc_number, value=value)
            self.output.send(msg)