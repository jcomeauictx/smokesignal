window.addEventListener("load", function() {
    const placeholder = "smokesignal transceiving...";
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
    const hashSize = 32;  // SHA-256 always produces 32 bytes
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
        if (updateHash) {
            let data = packet.slice(0, hashable),
                oldhash = packet.slice(hashable),
                newhash = lastScanned.slice(hashable);
            console.debug("changing packet hash from " +
                printable(oldhash) + " to " + printable(newhash)
            );
            packet = data + newhash;
        }
        console.debug("displaying new QR code: " + printable(packet));
        qrcode.makeCode(packet);
        sentText = document.getElementById("sent-text");
        sentText.textContent = lastShown = packet;
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
    const resultContainer = document.getElementById("received-text");
    lastScanned = bufferToString(new ArrayBuffer(chunkSize));
    const html5QrcodeScanner = new Html5QrcodeScanner(
        "qr-reader", {fps: 10, qrbox: 250});
    html5QrcodeScanner.render(onScanSuccess);

    /* process successfully scanned QR code */
    async function onScanSuccess(decodedText, decodedResult) {
        if (decodedText !== lastScanned) {
            console.debug(
                "decodedText: " + cleanup(decodedText) +
                ", length: " + decodedText.length +
                ", lastScanned: " + cleanup(lastScanned)
            );
            resultContainer.textContent = lastScanned = decodedText;
            let hash = decodedText.slice(hashable);
            console.debug("getting hash of scanned packet");
            let hashed = await arrayDataHash(stringToBuffer(
                lastShown.slice(0, hashable))
            );
            console.debug("comparing packet hash to hash of our QR code");
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
        } else {
            console.info("scanned text same as last time");
        }
    }

    /* clean up binary string for console logging */

    function printable(string) {
        return string.replace(/[^\r\n\x20-\x7E]/g, function(match) {
            return "\\x" + match.charCodeAt(0).toString(16).padStart(2, "0")
        }).replace(/[\r]/g, "\r").replace(/[\n]/g, "\n");
    }

    function oneline(string) {
        return string.replace(/[\r\n]+/g, " ");
    }

    function compressSpaces(string) {
        return string.replace(/ +/g, " ");
    }

    function cleanup(string) {
        return compressSpaces(oneline(string));
    }
    /* ArrayBuffer to binary string */
    // https://stackoverflow.com/a/71516276/493161

    function bufferToString(buffer) {
        const bytes = new Uint8Array(buffer);
        return bytes.reduce(function (string, byte) {
            return string + String.fromCharCode(byte);
        }, "");
    }

    /* binary string to ArrayBuffer */

    function stringToBuffer(string) {
        const buffer = new ArrayBuffer(string.length);
        const bytes = new Uint8Array(buffer);
        for (let i = 0; i < string.length; i++) {
            bytes[i] = string.charCodeAt(i);
        }
        return buffer;
    }

    /* binary string (big-endian) to integer */

    function binaryStringToInteger(string) {
        let result = 0;
        for (let i = 0; i < string.length; i++) {
            result = (result * 0x100) + string.charCodeAt(i);
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
        xhr.setRequestHeader("Content-Type", "application/octet-stream");
        xhr.onload = function(event) {
            console.debug("POST to /save returned " + xhr.response);
        };
        console.debug("POSTing: " + printable(packet));
        xhr.send(packet);
    }

    /* check layout, and move elements according to orientation */
    function setupPage() {
        const upper = document.getElementById("phone-upper");
        const lower = document.getElementById("phone-lower");
        /* width should be 0 on phone because that div is set display:none */
        const landscape = upper.firstElementChild.offsetWidth;
        let source, destination;
        if (landscape) {
            console.debug("looks horizontal (landscape)");
            [source, destination] = [lower, upper];
        } else {
            console.debug("looks vertical (profile)");
            [source, destination] = [upper, lower];
        }
        const boxes = ["sent-text", "received-text", "upload", "qr-reader"]
        for (let i = 0; i < boxes.length; i++) {
            let box = boxes[i] + "-container",
                from = source.getElementsByClassName(box)[0],
                to = destination.getElementsByClassName(box)[0];
            console.debug("moving " + box + " from " + from + " to " + to);
            to.append(...from.children);
        }
    }
    fileUpload.addEventListener("click", uploadFile);
    // enable page reshuffling on resize and orientationchange
    window.onresize = window.onorientationchange = setupPage;
    // and set it up now, at load time
    setupPage();
    // show a placeholder barcode now
    showPacket(chunkToPacket(placeholder));
    // run some tests on subroutines in lieu of doctests
    console.debug("packed integer 0: " + integerToBinaryString(0));
    console.debug("packed integer 0xffffffff: " +
        integerToBinaryString(0xffffffff));
    console.debug("unpacked \0\0\0\0: " + binaryStringToInteger("\0\0\0\0"));
    console.debug("unpacked \xff\xff\xff\xff: " +
        binaryStringToInteger("\xff\xff\xff\xff"));
    let testString = "\0\0\0\0\0\0\0\x10\xc3\xbf\xff\xffabcd\xff\xee\xdd\xcc";
    console.debug("printable(" + testString + "): " + printable(testString));
    testString = '{\n  "api": "blather",\n  "qrs": "tuv": {\n    "xyz": null}}'
    console.debug("cleanup(" + testString + "): " + cleanup(testString));
});
// vim: tabstop=8 shiftwidth=4 expandtab softtabstop=4
