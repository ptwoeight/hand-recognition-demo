window.onload = function() {
    refreshCameras();
    verifyMidi();
};

async function refreshCameras() {
    console.log("Scanning for hardware names...");
    // receives a list of objects: [{index: 0, name: "C922..."}, ...]
    let cameras = await eel.get_camera_list()();
    
    let select = document.querySelector('#camera-select');
    select.innerHTML = ''; 
    
    if (cameras.length === 0) {
        let opt = document.createElement('option');
        opt.innerHTML = "No Cameras Found";
        select.appendChild(opt);
    } else {
        cameras.forEach(cam => {
            let opt = document.createElement('option');
            opt.value = cam.index;   // Python uses this to open the port
            opt.innerHTML = cam.name; // User sees this "C922 Pro..."
            select.appendChild(opt);
        });
    }
}

async function verifyMidi() {
    let isReady = await eel.check_midi_status()(); 
    // let isReady = false; // uncomment to force-test blocked ui
    
    let startBtn = document.querySelector('#start-btn');
    let midiWarning = document.querySelector('#midi-warning');

    if (isReady) {
        startBtn.disabled = false;
        startBtn.style.opacity = "1";
        midiWarning.style.display = "none";
        console.log("MIDI System: Ready");
    } else {
        startBtn.disabled = true;
        startBtn.style.opacity = "0.3"; // Makes the button look "dead"
        midiWarning.style.display = "block"; // Shows your red/pink warning box
        console.log("MIDI System: loopMIDI not running");
    }
}

function updateCamera() {
    let index = document.querySelector('#camera-select').value;
    // Tell Python to switch the state.cap to this new index
    eel.set_camera_index(index);
}

function updateCamera() {
    let index = document.querySelector('#camera-select').value;
    eel.set_camera_index(index);
}

async function launch(mode) {
    hideAll();
    document.querySelector('#main-controls').style.display = 'block';
    document.querySelector('#ui-mode-text').innerText = mode;
    
    // Call Python to change mode
    await eel.change_mode(mode)();
}

async function startCalib() {
    hideAll();
    let calib = document.querySelector('#calib-screen');
    calib.style.display = 'block';
    // Trigger a tiny delay or use void offset to restart the animation
    void calib.offsetWidth; 
    calib.classList.add('screen-animate'); // Re-add the class to trigger the pop
    await eel.change_mode('CALIBRATE')();
    // Reset step in python and update UI
    nextStep(); 
}

async function nextStep() {
    let step = await eel.next_calibration_step()();
    
    if (step === 1) {
        document.querySelector('#calib-instruction').innerText = "With one hand, curl your fingers into a loose fist (show your nails to the camera).";
        document.querySelector('#step-indicator').innerText = "Step 1 / 2";
        document.querySelector('#back-from-calib').style.display = 'none';
    } else if (step === 2) {
        document.querySelector('#calib-instruction').innerText = "With the same hand, stretch your fingers as wide as possible!";
        document.querySelector('#step-indicator').innerText = "Step 2 / 2";
        document.querySelector('#back-from-calib').style.display = 'none';
    } else {
        // Step went back to 0 or finalized
        document.querySelector('#next-btn').style.display = 'none';
        document.querySelector('#cancel-btn').style.display = 'none';
        document.querySelector('#back-from-calib').style.display = 'block';
        document.querySelector('#calib-instruction').innerText = "Calibration Complete!\nThreshold Data Saved.";
    }
}

async function showInstructions() {
    hideAll();
    let instructions = document.querySelector('#instructions-screen');
    instructions.style.display = 'block';
    // Trigger a tiny delay or use void offset to restart the animation
    void instructions.offsetWidth; 
    instructions.classList.add('screen-animate'); // Re-add the class to trigger the pop
    instructions.change_mode('OFF')();
}

async function cancelCalib() {
    // Reset the step in Python back to 0
    await eel.reset_calibration()();
    // Return to the welcome menu
    showMenu();
}

function showMenu() {
    hideAll();
    let menu = document.querySelector('#welcome-screen');
    menu.style.display = 'block';
    // Trigger a tiny delay or use void offset to restart the animation
    void menu.offsetWidth; 
    menu.classList.add('screen-animate'); // Re-add the class to trigger the pop
    eel.change_mode('OFF')();
}

function hideAll() {
    document.querySelectorAll('.screen').forEach(s => {
        s.style.display = 'none';
        s.classList.remove('screen-animate'); // Remove the animation class
    });
}

function confirmExit()  {
    hideAll();
    let confirmExit = document.querySelector('#confirm-exit-screen');
    confirmExit.style.display = 'block';
    // Trigger a tiny delay or use void offset to restart the animation
    void confirmExit.offsetWidth; 
    confirmExit.classList.add('screen-animate'); // Re-add the class to trigger the pop
    eel.change_mode('OFF')();
}

function stopApp() {
    window.close();
    eel.stop_application()();
}

function showSettings() {
    hideAll();
    let settings = document.querySelector('#settings-screen');
    settings.style.display = 'block';
    // Trigger a tiny delay or use void offset to restart the animation
    void settings.offsetWidth; 
    settings.classList.add('screen-animate'); // Re-add the class to trigger the pop
    eel.change_mode('OFF')();
}

function showColorPicker() {
    hideAll();
    let color = document.querySelector('#color-screen');
    color.style.display = 'block';
    // Trigger a tiny delay or use void offset to restart the animation
    void color.offsetWidth; 
    color.classList.add('screen-animate'); // Re-add the class to trigger the pop
    eel.change_mode('OFF')();
}

function applyColor() {
    let color = document.querySelector('#ui-color-picker').value;
    // Update the CSS variable so the web UI matches the Python HUD
    document.documentElement.style.setProperty('--fl-pink', color);
    // Send to Python for OpenCV HUD
    eel.update_colors(color);
}