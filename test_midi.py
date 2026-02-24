import mido
import rtmidi

print("Mido Backend:", mido.backend)
print("All available outputs:", mido.get_output_names())