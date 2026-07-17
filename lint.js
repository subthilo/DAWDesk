const fs = require('fs');
try {
    const code = fs.readFileSync('daw_scripts/cubase/DAWDesk_Cubase.js', 'utf8');
    // Basic syntax check
    new Function(code);
    console.log("Syntax OK");
} catch (e) {
    console.log("Syntax Error:", e);
}
