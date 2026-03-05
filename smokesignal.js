window.addEventListener("load", function() {
    const fileUpload = document.getElementById("file-upload");
    const qrcodeElement = document.getElementById("qrcode");
    const qrcode = new QRCode(qrcodeElement, {
        width: qrcodeElement.offsetWidth,
        height: qrcodeElement.offsetHeight,
        correctLevel: QRCode.CorrectLevel.L
    });
    let lastQrData = null;

    /* Scanner setup */
    const resultContainer = document.getElementById("scan-results");
    let lastResult = null;

    function onScanSuccess(decodedText, decodedResult) {
        console.debug("onScanSuccess() called");
        console.debug("decodedText: " + decodedText +
                    ", length: " + decodedText.length +
                    ", decodedResult: " + decodedResult +
                    ", lastResult" + lastResult);
        if (decodedText !== lastResult) {
            lastResult = decodedText;
            /* decodedText may be text; for binary protocol we need
               to base64-encode it for transport to the backend.
               html5-qrcode gives us text, so we encode to base64. */
            let b64;
            b64 = btoa(decodedText);
            /* it may contain chars > 255, so encode via TextEncoder */
            const bytes = new TextEncoder().encode(decodedText);
            b64 = btoa(String.fromCharCode.apply(null, bytes));
            resultContainer.textContent = decodedText;
            const xhr = new XMLHttpRequest();
            xhr.open("POST", "/scan", true);
            xhr.onload = function() {
                if (xhr.status == 200) {
                    console.log("/scan post successful");
                } else {
                    console.error("/scan post status: " + xhr.status);
                }
            };
            xhr.onerror = function() {
                console.error("/scan post failed");
            };
            xhr.send(JSON.stringify({data: b64}));
        }
    }

    const html5QrcodeScanner = new Html5QrcodeScanner(
        "qr-reader", {fps: 10, qrbox: 250});
    html5QrcodeScanner.render(onScanSuccess);

    /* Poll backend for QR data to display to peer */
    function pollQrData() {
        fetch("/qrdata")
            .then(function(r) { return r.json(); })
            .then(function(j) {
                if (j.data && j.data !== lastQrData) {
                    lastQrData = j.data;
                    /* data is base64-encoded binary; QRCode.js can
                       handle raw strings, decode b64 to binary string */
                    let raw = atob(j.data);
                    qrcode.makeCode(raw);
                } else if (!j.data && lastQrData) {
                    lastQrData = null;
                    qrcode.clear();
                }
            })
            .catch(function(err) { console.error("poll failed:", err); });
    }
    setInterval(pollQrData, 500);

    /* ArrayBuffer to binary string */
    // https://stackoverflow.com/a/71516276/493161

    function bufferToString(buffer) {
        const bytes = new Uint8Array(buffer);
        return bytes.reduce(function (string, byte) {
            return string + String.fromCharCode(byte);
        }, "");
    }

    /* Upload file to send */
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
            for (let i = 0; i < data.length; i += 256) {
                console.debug("showing chunk of " + file +
                              " starting at index " + i);
                qrcode.makeCode(data.substring(i, i + 256));
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
    qrcode.makeCode("Smokesignal transceiving...");
});
// vim: tabstop=8 shiftwidth=4 expandtab softtabstop=4
