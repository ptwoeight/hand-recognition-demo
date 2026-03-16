# config 1: toggle arm

- left hand selects insert
  - thumb toggles arm on selected insert
    - inserts 1-5: index, mid, <u>ring</u>, mid + ring, ring + pinky

      **OR**

    - inserts 1-5: <u>thumb</u>, index, mid, mid + ring, ring + pinky

- right hand performs insert volume automation

# config: toggle mute

- left hand toggles mute on selected insert
  - inserts 1-5: thumb, index, mid, mid + ring, ring + pinky

- right hand functions:
  - index: select insert on left of current
  - mid + ring + pinky: select insert on right of current
  - thumb: toggle arm on selected insert

---

both configs will need different gesture control logic files
might also need separate gesturecontroller scripts for fl studio but would prefer one to prevent the user manually having to switch the script in fl

- have the ui or cam show what config they chose in settings before starting recording (like a lil msg in the corner)

---

# to do

1. ~~reorganise file structure for eel implementation~~
   - ~~there will be a separate folder called GestureController for the script so they can add it to their FL directory (the script)~~
2. create separate gesture logic (per config)
3. create separate scripts
4. create ui
5. create calibration feature (changes threshold values)
   - will require changing some gesture logic accordingly but hopefully not too drastic of an adjustment
     > this feature is considered OPTIONAL to implement. if not implemented, project will be described currently as a prototype currently tailored to personal threshold information.
