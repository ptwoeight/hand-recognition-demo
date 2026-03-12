import mido

# Force a fresh look at the system
mido.set_backend('mido.backends.rtmidi')

print("--- SYSTEM SCAN ---")
print(f"Backend: {mido.backend}")
print(f"Ports found: {mido.get_output_names()}")

target = 'GesturePort 1'

if target in mido.get_output_names():
    try:
        out = mido.open_output(target)
        print(f"\n🎉 SUCCESS! Connected to {target}")
        out.close()
    except Exception as e:
        print(f"\n❌ FOUND BUT BLOCKED: {e}")
else:
    print(f"\n❌ NOT FOUND: '{target}' is missing from the list above.")