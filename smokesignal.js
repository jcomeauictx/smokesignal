window.addEventListener("load", function() {
    const fileUpload = document.getElementById("file-upload");
    const qrcodeElement = document.getElementById("qrcode");
    const qrcode = new QRCode(qrcodeElement, {
        width: qrcodeElement.offsetWidth,
        height: qrcodeElement.offsetHeight,
        correctLevel: QRCode.CorrectLevel.L
    });
    // for third arg to xhr.open, can never remember what it's for
    const asynchronous = true, synchronous = false;
    // ideally pull the following constants from smokesignal/wsgi
    const chunkSize = 128;
    const intSize = 4;
    const serialSize = 4;
    const hashable = serialSize + intSize + chunkSize;
    const hashSize = arrayDataHash(new ArrayBuffer(0)).length;
    // set some state variables
    let lastScanned = null;
    let lastShown = null;
    let dataBeingSent = null;
    let currentDataSerial = 0;

    /* convert a raw file chunk into a valid data packet */
    function chunkToPacket(chunk, serial) {
        const padding = bufferToString(
            new ArrayBuffer(chunkSize - chunk.length));
        const packedSerial = integerToBinaryString(serial, serialSize);
        const packedSize = integerToBinaryString(chunk.length, intSize);
        const hashDigest = lastScanned.slice(hashable);
        return packedSerial + packedSize + chunk + padding + hashDigest;
    }

    /* display QR code and save in global `lastShown` */
    function showPacket(packet, updateHash=false) {
        if (updateHash)
            packet = packet.slice(0, hashable) + lastScanned.slice(hashable);
        qrcode.makeCode(packet);
        lastShown = packet;
    };

    /* break packed `packet` back down into components */
    function packetToData(packet) {
        let offset = serialSize;
        const serial = binaryStringToInteger(packet.slice(0, offset));
        const size = binaryStringToInteger(
            packet.slice(offset, offset + intSize));
        offset += intSize;
        const chunk = packet.slice(offset, offset + chunkSize);
        offset += chunkSize;
        const hash = packet.slice(offset, offset + hashSize);
        return [serial, size, chunk, hash];
    }

    /* scanner setup */
    const resultContainer = document.getElementById("scan-results");
    lastScanned = bufferToString(new ArrayBuffer(chunkSize));

    function onScanSuccess(decodedText, decodedResult) {
        console.debug("onScanSuccess() called");
        console.debug("decodedText: " + decodedText +
                    ", length: " + decodedText.length +
                    ", decodedResult: " + decodedResult +
                    ", lastScanned" + lastScanned);
        if (decodedText !== lastScanned) {
            lastScanned = decodedText;  // updates webpage
            let hash = decodedText.slice(hashable);
            let hashed = arrayDataHash(lastShown.slice(0, hashable));
            let data = dataBeingSent;
            if (hash == hashed) {
                console.log("peer saw our current QR code");
                if (data != null) {
                    let serial = ++currentDataSerial;
                    let offset = serial * chunkSize;
                    let chunk = data.slice(offset, offset + chunkSize);
                    if (!chunk) {
                        console.debug("file upload complete");
                        dataBeingSent = null;
                        currentDataSerial = 0;
                    } else lastShown = chunkToPacket(chunk, serial);
                } else console.debug("acking placeholder QR code on peer");
            }
            // redisplay current outgoing QR code with updated hash
            // it's what lets peer know we saw its last code, AND
            // if lastShown was updated above, it sends new packet to peer
            showPacket(lastShown, true);
            // save newly received packet
            savePacket(lastScanned);
        }
    }

    const html5QrcodeScanner = new Html5QrcodeScanner(
        "qr-reader", {fps: 10, qrbox: 250});
    html5QrcodeScanner.render(onScanSuccess);

    /* ArrayBuffer to binary string */
    // https://stackoverflow.com/a/71516276/493161

    function bufferToString(buffer) {
        const bytes = new Uint8Array(buffer);
        return bytes.reduce(function (string, byte) {
            return string + String.fromCharCode(byte);
        }, "");
    }

    /* binary string (big-endian) to integer */

    function binaryStringToInteger(string) {
        let result = 0;
        for (let i = 0; i < string.length; i++) {
            result = (result << 8) + string.charCodeAt(i);
        }
        return result;
    }

    /* hash of ArrayBuffer */
    async function arrayDataHash(data) {
        const hash = await window.crypto.subtle.digest("SHA-256", data);
        return bufferToString(hash);
    };

    /* integer to big-endian binary string */
    function integerToBinaryString(integer, length=4) {
        let result = "";
        for (let i = 0; i < length; i++) {
            result = String.fromCharCode(integer % 256) + result;
            integer >>= 8;
        }
        return result;
    }

    /* send file to peer */
    function uploadFile() {
        const input = document.getElementById("file-input");
        if (!input.files.length) {
            alert("Select a file first");
            return;
        }
        const file = input.files[0];
        console.debug("about to send file " + file);
        const reader = new FileReader();
        reader.onload = function(event) {
            console.debug("file " + file + " has been read");
            dataBeingSent = bufferToString(reader.result);
            currentDataSerial = 0;
            // show first packet; the rest will be event-driven
            showPacket(chunkToPacket(dataBeingSent.slice(0, chunkSize), 0));
        };
        reader.readAsArrayBuffer(file);
    }

    /* save chunk to device, only thing we can't do in JavaScript */
    function savePacket(packet) {
        const xhr = new XMLHttpRequest();
        xhr.open("POST", "/save", asynchronous);
        xhr.onload = function(eventInstance) {
            console.log("POST to /save returned " + xhr.response);
        };
        xhr.sendAsBinary(packet);
    }

    /* check if phone, and if so, make hidden elements visible */
    function setupPhone() {
        const upper = document.getElementById("phone-upper");
        const lower = document.getElementById("phone-lower");
        const leftPanel = upper.firstElementChild;
        const rightPanel = upper.lastElementChild;
        const width = leftPanel.offsetWidth;
        /* width should be 0 on phone because that div is set display:none */
        console.debug("left panel: " + leftPanel + ", width: " + width);
        if (width == 0) {
            console.debug("looks like a phone");
            while (leftPanel.firstElementChild) {
                lower.appendChild(leftPanel.firstElementChild)
            }
            while (rightPanel.firstElementChild) {
                lower.appendChild(rightPanel.firstElementChild)
            }
            console.debug("moved children of left and right panels lower");
        } else {
            console.debug("doesn't appear to be a phone, left DOM as is");
        }
    }
    fileUpload.addEventListener("click", uploadFile);
    setupPhone();
    showPacket(chunkToPacket("Smokesignal transceiving..."));
});
// vim: tabstop=8 shiftwidth=4 expandtab softtabstop=4
