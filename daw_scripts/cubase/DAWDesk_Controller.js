// DAWDesk Cubase MIDI Remote Script
// 14-Bit SysEx Integration (Manufacturer 7D)
// Place this in: \Documents\Steinberg\Cubase\MIDI Remote\Driver Scripts\Local\DAWDesk\Controller

var midiremote_api = require('midiremote_api_v1');

// Create device driver
var deviceDriver = midiremote_api.makeDeviceDriver('DAWDesk', 'Controller', 'DAWDesk Team');

// Setup MIDI ports
var midiInput = deviceDriver.mPorts.makeMidiInput();
var midiOutput = deviceDriver.mPorts.makeMidiOutput();

// Define surface
var deviceSurface = deviceDriver.mSurface;

// Map maximum 64 channels for now
var NUM_CHANNELS = 64;

var faderElements = [];
var panElements = [];
var faderVars = [];
var panVars = [];

for (var i = 0; i < NUM_CHANNELS; ++i) {
    // Fader
    var fader = deviceSurface.makeFader(0, i, 1, 3);
    var faderVar = deviceSurface.makeCustomValueVariable('Fader_' + i);
    
    // We bind the graphic fader directly to the custom variable so the UI updates
    fader.mSurfaceValue.mOnProcessValueChange = function(activeDevice, value, diff) {
        // We do not need this direction. Wait, mSurfaceValue binding to CustomVar?
    };
    
    faderElements.push(fader);
    faderVars.push(faderVar);
    
    // Pan
    var pan = deviceSurface.makeKnob(1, i, 1, 1);
    var panVar = deviceSurface.makeCustomValueVariable('Pan_' + i);
    panElements.push(pan);
    panVars.push(panVar);
}

// Map to Host (Mixer)
var page = deviceDriver.mMapping.makePage('Mixer');
var hostMixerBank = page.mHostAccess.mMixConsole.makeMixerBankZone('Bank')

for (var i = 0; i < NUM_CHANNELS; ++i) {
    var hostChannel = hostMixerBank.makeMixerBankChannel();
    
    // Bind Custom Variables to Host (this enables Cubase to read/write from our variables)
    page.makeValueBinding(faderVars[i], hostChannel.mValue.mVolume);
    page.makeValueBinding(panVars[i], hostChannel.mValue.mPan);
    
    // Bind Graphic Surface Elements directly to host so the on-screen UI reflects the state
    page.makeValueBinding(faderElements[i].mSurfaceValue, hostChannel.mValue.mVolume);
    page.makeValueBinding(panElements[i].mSurfaceValue, hostChannel.mValue.mPan);
}

// --- HARDWARE TO CUBASE (Input) ---
midiInput.mOnSysex = function(activeDevice, midiMessage) {
    // F0 7D cmd track msb lsb F7
    if (midiMessage.length === 7 && midiMessage[1] === 0x7D) {
        var cmd = midiMessage[2];
        var track = midiMessage[3];
        var msb = midiMessage[4];
        var lsb = midiMessage[5];
        
        var val_14 = (msb << 7) | lsb;
        var float_val = val_14 / 16383.0;
        
        if (track >= 0 && track < NUM_CHANNELS) {
            if (cmd === 0x01) { // Volume
                faderVars[track].setProcessValue(activeDevice, float_val);
            } else if (cmd === 0x02) { // Pan
                panVars[track].setProcessValue(activeDevice, float_val);
            }
        }
    }
};

// --- CUBASE TO HARDWARE (Feedback/Output) ---
for (var i = 0; i < NUM_CHANNELS; ++i) {
    (function(trackIndex) {
        faderVars[trackIndex].mOnProcessValueChange = function(activeDevice, value, diff) {
            var val_14 = Math.round(value * 16383);
            var msb = (val_14 >> 7) & 0x7F;
            var lsb = val_14 & 0x7F;
            midiOutput.sendMidi(activeDevice, [0xF0, 0x7D, 0x01, trackIndex, msb, lsb, 0xF7]);
        };
        
        panVars[trackIndex].mOnProcessValueChange = function(activeDevice, value, diff) {
            var val_14 = Math.round(value * 16383);
            var msb = (val_14 >> 7) & 0x7F;
            var lsb = val_14 & 0x7F;
            midiOutput.sendMidi(activeDevice, [0xF0, 0x7D, 0x02, trackIndex, msb, lsb, 0xF7]);
        };
    })(i);
}

console.log("DAWDesk Cubase SysEx Script loaded.");
