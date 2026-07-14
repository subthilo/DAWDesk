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

var NUM_CHANNELS = 60; // Internal buffer, max supported tracks per bank
var faderElements = [];
var panElements = [];
var soloElements = [];
var muteElements = [];
var meterElements = [];
var labelElements = [];
var lastTitle = [];   // Cache: last sent title per channel

for (var c = 0; c < NUM_CHANNELS; c++) {
    lastTitle.push('');
}

// -------------------------------------------------------------------------
// SURFACE ELEMENTS
// -------------------------------------------------------------------------
for (var i = 0; i < NUM_CHANNELS; ++i) {
    (function(index) {
        var fader = deviceSurface.makeFader(index * 2, 2, 2, 4);
        var pan = deviceSurface.makeKnob(index * 2, 0, 2, 2);
        var solo = deviceSurface.makeButton(index * 2, 7, 1, 1);
        var mute = deviceSurface.makeButton(index * 2 + 1, 7, 1, 1);
        
        // CRITICAL: A Fader alone does not trigger Text callbacks. We MUST create a Label
        var label = deviceSurface.makeLabelField(index * 2, 6, 2, 1);
        
        faderElements.push(fader);
        panElements.push(pan);
        soloElements.push(solo);
        muteElements.push(mute);
        labelElements.push(label);
        
        // Fader = CC 1..5, 7..31 (MSB), skip CC 6 (Data Entry, intercepted by Cubase NRPN)
        var msb = 1 + (index % 30);
        if (msb >= 6) msb++;  // Skip CC 6
        var faderCh = Math.floor(index / 30);
        
        fader.mSurfaceValue.mMidiBinding
            .setInputPort(midiInput)
            .setOutputPort(midiOutput)
            .bindToControlChange14Bit(faderCh, msb);

        // Pan = Base Ch 4. Uses Ch 4 and 5. CC 1..60
        var panCh = 4 + Math.floor(index / 60);
        var panCC = 1 + (index % 60);
        pan.mSurfaceValue.mMidiBinding
            .setInputPort(midiInput)
            .setOutputPort(midiOutput)
            .bindToControlChange(panCh, panCC);

        // Solo = Base Ch 6. Uses Ch 6 and 7. CC 1..60
        var soloCh = 6 + Math.floor(index / 60);
        var soloCC = 1 + (index % 60);
        solo.mSurfaceValue.mMidiBinding
            .setInputPort(midiInput)
            .setOutputPort(midiOutput)
            .bindToControlChange(soloCh, soloCC);

        // Mute = Base Ch 8. Uses Ch 8 and 9. CC 1..60
        var muteCh = 8 + Math.floor(index / 60);
        var muteCC = 1 + (index % 60);
        mute.mSurfaceValue.mMidiBinding
            .setInputPort(midiInput)
            .setOutputPort(midiOutput)
            .bindToControlChange(muteCh, muteCC);

        // VU Meter = Base Ch 10. Uses Ch 10 and 11. CC 1..60
        var meter = deviceSurface.makeKnob(index * 2, 10, 1, 1);
        var meterCh = 10 + Math.floor(index / 60);
        var meterCC = 1 + (index % 60);
        meter.mSurfaceValue.mMidiBinding
            .setOutputPort(midiOutput)
            .bindToControlChange(meterCh, meterCC);
        meterElements.push(meter);
            
        // We do NOT bind MIDI to the label. We just need it to exist to receive Text.
    })(i);
}

// -------------------------------------------------------------------------
// TRANSPORT & GLOBAL ELEMENTS
// -------------------------------------------------------------------------
var playButton = deviceSurface.makeButton(0, 12, 1, 2);
var stopButton = deviceSurface.makeButton(1, 12, 1, 2);
var recordButton = deviceSurface.makeButton(2, 12, 2, 2);
var cycleButton = deviceSurface.makeButton(4, 12, 2, 2);

playButton.mSurfaceValue.mMidiBinding.setInputPort(midiInput).setOutputPort(midiOutput).bindToNote(14, 104);
stopButton.mSurfaceValue.mMidiBinding.setInputPort(midiInput).setOutputPort(midiOutput).bindToNote(14, 105);
recordButton.mSurfaceValue.mMidiBinding.setInputPort(midiInput).setOutputPort(midiOutput).bindToNote(14, 106);
cycleButton.mSurfaceValue.mMidiBinding.setInputPort(midiInput).setOutputPort(midiOutput).bindToNote(14, 107);

// -------------------------------------------------------------------------
// PAGE & BINDINGS
// -------------------------------------------------------------------------
var page = deviceDriver.mMapping.makePage('Mixer');

// Bind Transport
page.makeValueBinding(playButton.mSurfaceValue, page.mHostAccess.mTransport.mValue.mStart).setTypeToggle();
page.makeValueBinding(stopButton.mSurfaceValue, page.mHostAccess.mTransport.mValue.mStop).setTypeToggle();
page.makeValueBinding(recordButton.mSurfaceValue, page.mHostAccess.mTransport.mValue.mRecord).setTypeToggle();
page.makeValueBinding(cycleButton.mSurfaceValue, page.mHostAccess.mTransport.mValue.mCycleActive).setTypeToggle();

// Create Mixer Bank Zone (Excluding Inputs and Outputs)
var hostMixerBankZone = page.mHostAccess.mMixConsole.makeMixerBankZone('MixerBankZone')
    .excludeInputChannels()
    .excludeOutputChannels();



var nudgeBankLeft = deviceSurface.makeButton(0, 8, 2, 2);
nudgeBankLeft.mSurfaceValue.mMidiBinding.setInputPort(midiInput).bindToControlChange(14, 126);
page.makeActionBinding(nudgeBankLeft.mSurfaceValue, hostMixerBankZone.mAction.mPrevBank);

var nudgeBankRight = deviceSurface.makeButton(2, 8, 2, 2);
nudgeBankRight.mSurfaceValue.mMidiBinding.setInputPort(midiInput).bindToControlChange(14, 127);
page.makeActionBinding(nudgeBankRight.mSurfaceValue, hostMixerBankZone.mAction.mNextBank);



for (var i = 0; i < NUM_CHANNELS; ++i) {
    (function(index) {
        var channelBankItem = hostMixerBankZone.makeMixerBankChannel();
        
        // Bind Fader to Volume
        page.makeValueBinding(faderElements[index].mSurfaceValue, channelBankItem.mValue.mVolume);
        
        // Bind Pan to Pan
        page.makeValueBinding(panElements[index].mSurfaceValue, channelBankItem.mValue.mPan);
        
        // Bind Solo
        page.makeValueBinding(soloElements[index].mSurfaceValue, channelBankItem.mValue.mSolo);
        
        // Bind Mute
        page.makeValueBinding(muteElements[index].mSurfaceValue, channelBankItem.mValue.mMute);
        
        // Bind VU Meter
        page.makeValueBinding(meterElements[index].mSurfaceValue, channelBankItem.mValue.mVUMeter);
        
        // Track Name (cached – only send when title actually changes)
        channelBankItem.mValue.mVolume.mOnTitleChange = function(activeDevice, activeMapping, objectTitle) {
            var str = objectTitle ? objectTitle.toString() : "";
            if (str === lastTitle[index]) return; // No change → skip
            lastTitle[index] = str;
            var maxLen = Math.min(str.length, 20);
            midiOutput.sendMidi(activeDevice, [0xBE, 115, index]); // Start Title Transfer
            for (var j = 0; j < maxLen; j++) {
                midiOutput.sendMidi(activeDevice, [0xBE, 117, str.charCodeAt(j) & 0x7F]); // Char
            }
            midiOutput.sendMidi(activeDevice, [0xBE, 118, 0]); // End Transfer
        };
        
        // Send Track Color – always forward, colors change rarely so no cache needed.
        faderElements[index].mSurfaceValue.mOnColorChange = function(activeDevice, r, g, b, a, isActive) {
            var ri = Math.round(r * 127);
            var gi = Math.round(g * 127);
            var bi = Math.round(b * 127);
            midiOutput.sendMidi(activeDevice, [0xBE, 120, index]);
            midiOutput.sendMidi(activeDevice, [0xBE, 121, ri]);
            midiOutput.sendMidi(activeDevice, [0xBE, 122, gi]);
            midiOutput.sendMidi(activeDevice, [0xBE, 123, bi]);
        };
    })(i);
}

console.log("DAWDesk Cubase Script loaded.");
