var midiremote_api = require('midiremote_api_v1');

var deviceDriver = midiremote_api.makeDeviceDriver('DAWDesk', 'Controller', 'DAWDesk Team');

// Setup MIDI ports
var midiInput = deviceDriver.mPorts.makeMidiInput();
var midiOutput = deviceDriver.mPorts.makeMidiOutput();

deviceDriver.makeDetectionUnit().detectPortPair(midiInput, midiOutput)
    .expectInputNameEquals('DAWDesk')
    .expectOutputNameEquals('DAWDesk');

// Define surface
var deviceSurface = deviceDriver.mSurface;

var NUM_CHANNELS = 30; // Internal buffer, max supported tracks per controller per routing page
var faderElements = [];
var panElements = [];
var labelElements = []; // We need labels to receive Title/DisplayValue changes!

// -------------------------------------------------------------------------
// SURFACE ELEMENTS
// -------------------------------------------------------------------------
for (var i = 0; i < NUM_CHANNELS; ++i) {
    (function(index) {
        var fader = deviceSurface.makeFader(index * 2, 2, 2, 4);
        var pan = deviceSurface.makeKnob(index * 2, 0, 2, 2);
        
        // ** CRITICAL: A Fader alone does not trigger Text callbacks. We MUST create a Label **
        var label = deviceSurface.makeLabelField(index * 2, 6, 2, 1);
        
        faderElements.push(fader);
        panElements.push(pan);
        labelElements.push(label);
        
        // Fader = CC 1..30 (MSB) + CC 33..62 (LSB), Channel 0-2
        var msb = 1 + (index % 30);
        var lsb = 33 + (index % 30);
        var faderCh = Math.floor(index / 30);
        
        fader.mSurfaceValue.mMidiBinding
            .setInputPort(midiInput)
            .setOutputPort(midiOutput)
            .bindToControlChange(faderCh, msb)
            .bindToControlChange(faderCh, lsb);

        // Pan = CC 64..93, Channel 0-2
        var panCh = Math.floor(index / 30);
        var panCC = 64 + (index % 30);
        pan.mSurfaceValue.mMidiBinding
            .setInputPort(midiInput)
            .setOutputPort(midiOutput)
            .bindToControlChange(panCh, panCC);
            
        // We do NOT bind MIDI to the label. We just need it to exist to receive Text.
    })(i);
}

// -------------------------------------------------------------------------
// PAGE & BINDINGS
// -------------------------------------------------------------------------
var page = deviceDriver.mMapping.makePage('Mixer');

// Create Mixer Bank Zone
var hostMixerBankZone = page.mHostAccess.mMixerAccess.makeMixerBankZone('MixerBankZone');

// Add Nudge bindings
var nudgeLeft = deviceSurface.makeButton(0, 8, 2, 2);
nudgeLeft.mSurfaceValue.mMidiBinding.setInputPort(midiInput).bindToControlChange(14, 126);
page.makeActionBinding(nudgeLeft.mSurfaceValue, hostMixerBankZone.mAction.mPrevBank);

var nudgeRight = deviceSurface.makeButton(2, 8, 2, 2);
nudgeRight.mSurfaceValue.mMidiBinding.setInputPort(midiInput).bindToControlChange(14, 127);
page.makeActionBinding(nudgeRight.mSurfaceValue, hostMixerBankZone.mAction.mNextBank);

for (var i = 0; i < NUM_CHANNELS; ++i) {
    (function(index) {
        var channelBankItem = hostMixerBankZone.makeMixerBankChannel();
        
        // Bind Fader to Volume
        page.makeValueBinding(faderElements[index].mSurfaceValue, channelBankItem.mValue.mVolume);
        
        // Bind Pan to Pan
        page.makeValueBinding(panElements[index].mSurfaceValue, channelBankItem.mValue.mPan);
        
        // ** CRITICAL: Hook into the Fader's mSurfaceValue, which has a MIDI binding! **
        faderElements[index].mSurfaceValue.mOnTitleChange = function(activeDevice, objectTitle, valueTitle) {
            var str = objectTitle ? objectTitle.toString() : "";
            var maxLen = Math.min(str.length, 20);
            midiOutput.sendMidi(activeDevice, [0xBE, 115, index]); // Start Title Transfer
            for (var j = 0; j < maxLen; j++) {
                midiOutput.sendMidi(activeDevice, [0xBE, 117, str.charCodeAt(j) & 0x7F]); // Char
            }
            midiOutput.sendMidi(activeDevice, [0xBE, 118, 0]); // End Transfer
        };
        
        // Send Display Value (z.B. "-5.0 dB")
        faderElements[index].mSurfaceValue.mOnDisplayValueChange = function(activeDevice, valueString, valueString2) {
            var str = valueString ? valueString.toString() : "";
            var maxLen = Math.min(str.length, 20);
            midiOutput.sendMidi(activeDevice, [0xBE, 116, index]); // Start Value Transfer
            for (var j = 0; j < maxLen; j++) {
                midiOutput.sendMidi(activeDevice, [0xBE, 117, str.charCodeAt(j) & 0x7F]); // Char
            }
            midiOutput.sendMidi(activeDevice, [0xBE, 118, 0]); // End Transfer
        };
    })(i);
}

// -------------------------------------------------------------------------
// INITIALIZATION & DEBUG
// -------------------------------------------------------------------------
var debugBtn = deviceSurface.makeButton(4, 8, 2, 2);
debugBtn.mSurfaceValue.mMidiBinding.setInputPort(midiInput).bindToControlChange(14, 111);
debugBtn.mSurfaceValue.mOnProcessValueChange = function(activeDevice, value, diff) {
    if (value > 0) {
        var str = "ABC";
        midiOutput.sendMidi(activeDevice, [0xBE, 119, 0]); // Start Debug Transfer
        for (var j = 0; j < str.length; j++) {
            midiOutput.sendMidi(activeDevice, [0xBE, 117, str.charCodeAt(j) & 0x7F]);
        }
        midiOutput.sendMidi(activeDevice, [0xBE, 118, 0]); // End Transfer
    }
};

console.log("DAWDesk Cubase Script loaded.");
