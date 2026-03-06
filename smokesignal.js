window.addEventListener("load", function() {
    const fileUpload = document.getElementById("file-upload");
    const qrcodeElement = document.getElementById("qrcode");
    const qrcode = new QRCode(qrcodeElement, {
        width: qrcodeElement.offsetWidth,
        height: qrcodeElement.offsetHeight,
        correctLevel: QRCode.CorrectLevel.L
    });
    // ideally pull the following constants from smokesignal/wsgi
    const chunkSize = 128;
    const intSize = 4;
    const serialSize = 4;
    const hashable = serialSize + intSize + chunkSize;
    const hashSize = arrayDataHash(new ArrayBuffer(0)).length;
    // set some state variables
    let lastScanned = null;
    let lastShown = null;

    /* Convert a raw file chunk into a valid data packet */
    function chunkToPacket(chunk, serial) {
        const padding = bufferToString(
            new ArrayBuffer(chunkSize - chunk.length));
        const packedSerial = integerToBinaryString(serial, serialSize);
        const packedSize = integerToBinaryString(chunk.length, intSize);
        const hashDigest = lastScanned.slice(hashable);
        return packedSerial + packedSize + chunk + padding + hashDigest;
    }

    /* Display QR code and save in global `lastShown` */
    function showPacket(packet, updateHash=false) {
        if (updateHash)
            packet = packet.slice(0, hashable) + lastScanned.slice(hashable);
        qrcode.makeCode(packet);
        lastShown = packet;
    };

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

    /* Scanner setup */
    const resultContainer = document.getElementById("scan-results");
    lastScanned = bufferToString(new ArrayBuffer(chunkSize));

    function onScanSuccess(decodedText, decodedResult) {
        console.debug("onScanSuccess() called");
        console.debug("decodedText: " + decodedText +
                    ", length: " + decodedText.length +
                    ", decodedResult: " + decodedResult +
                    ", lastScanned" + lastScanned);
        if (decodedText !== lastScanned) {
            lastScanned = decodedText;
            // redisplay current outgoing QR code with updated hash
            // it's what lets peer know we saw its last code
            showPacket(lastShown, true);
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

    /* Binary string (big-endian) to integer */

    function binaryStringToInteger(string) {
        let result = 0;
        for (let i = 0; i < string.length; i++) {
            result = (result << 8) + string.charCodeAt(i);
        }
        return result;
    }

    async function arrayDataHash(data) {
        const hash = await window.crypto.subtle.digest("SHA-256", data);
        return bufferToString(hash);
    };

    /* Integer to big-endian binary string */
    function integerToBinaryString(integer, length=4) {
        let result = "";
        for (let i = 0; i < length; i++) {
            result = String.fromCharCode(integer % 256) + result;
            integer >>= 8;
        }
        return result;
    }

    /* Send file to peer */
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
            const data = bufferToString(reader.result);
            for (let i = 0, j = 0; i < data.length; i += 256, j++) {
                console.debug("showing chunk " + j + " of " + file +
                              " starting at index " + i);
                showPacket(chunkToPacket(
                    data.substring(i, i + chunkSize), j)
                );
            }
        };
        reader.readAsArrayBuffer(file);
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
