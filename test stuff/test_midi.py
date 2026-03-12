import mido
import os

# 1. Force the Pygame backend (Much more stable for your current setup)
try:
    os.environ['MIDO_BACKEND'] = 'mido.backends.pygame'
    # We explicitly import and init pygame.midi to wake up the driver
    import pygame.midi
    pygame.midi.init()
    print("✅ Pygame MIDI Backend Loaded")
except Exception as e:
    print(f"❌ Backend Load Error: {e}")

print("\n--- SYSTEM SCAN ---")
available_ports = mido.get_output_names()
print(f"Ports found: {available_ports}")

# 2. Smart Search: Look for ANY port containing our name
# This solves the "FLGesturePort 1 1" issue automatically
target_substring = 'FLGesture' 
matches = [p for p in available_ports if target_substring in p]

if matches:
    target = matches[0] # Take the first match found
    try:
        out = mido.open_output(target)
        print(f"\n🎉 SUCCESS! Connected to: {target}")
        out.close()
    except Exception as e:
        print(f"\n❌ FOUND BUT BLOCKED: {e}")
else:
    print(f"\n❌ NOT FOUND: No ports containing '{target_substring}' were detected.")
    print("Tip: Make sure loopMIDI is running and a port is created.")