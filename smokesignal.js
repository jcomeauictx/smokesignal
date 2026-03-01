window.addEventListener("load", function() {
    var qrcode = new QRCode(document.getElementById("qrcode"), {
        width: 200,
        height: 200,
        correctLevel: QRCode.CorrectLevel.L
    });
    var lastQrData = null;

    /* Scanner setup */
    var resultContainer = document.getElementById("scan-results");
    var lastResult = null;

    function onScanSuccess(decodedText, decodedResult) {
        if (decodedText !== lastResult) {
            lastResult = decodedText;
            /* decodedText may be text; for binary protocol we need
               to base64-encode it for transport to the backend.
               html5-qrcode gives us text, so we encode to base64. */
            var b64;
            try {
                b64 = btoa(decodedText);
            } catch(e) {
                /* if it contains chars > 255, encode via TextEncoder */
                var bytes = new TextEncoder().encode(decodedText);
                b64 = btoa(String.fromCharCode.apply(null, bytes));
            }
            resultContainer.textContent = "Scanned " +
                decodedText.length + " bytes, serial=" +
                decodedText.charCodeAt(3);
            fetch("/scan", {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify({data: b64})
            }).catch(function(err) {
                console.error("scan post failed:", err);
            });
        }
    }

    var html5QrcodeScanner = new Html5QrcodeScanner(
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
                    var raw = atob(j.data);
                    qrcode.makeCode(raw);
                } else if (!j.data && lastQrData) {
                    lastQrData = null;
                    qrcode.clear();
                }
            })
            .catch(function(err) { console.error("poll failed:", err); });
    }
    setInterval(pollQrData, 500);

    /* Poll status */
    function pollStatus() {
        fetch("/status")
            .then(function(r) { return r.json(); })
            .then(function(j) {
                var el = document.getElementById("status");
                var text = "Status: " + j.status;
                if (j.sending) text += " | Sending: " + j.sending;
                if (j.receiving) text += " | Receiving: " + j.receiving;
                text += " | Packet #" + j.serial;
                el.textContent = text;
            })
            .catch(function(err) { console.error("status failed:", err); });
    }
    setInterval(pollStatus, 1000);

    /* Upload file to send */
    function uploadFile() {
        var input = document.getElementById("file-input");
        if (!input.files.length) {
            alert("Select a file first");
            return;
        }
        var file = input.files[0];
        var reader = new FileReader();
        reader.onload = function(e) {
            var b64 = btoa(String.fromCharCode.apply(null,
                new Uint8Array(e.target.result)));
            fetch("/upload", {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify({data: b64, filename: file.name})
            }).then(function(r) { return r.json(); })
              .then(function(j) {
                  if (j.ok) alert("Sending " + file.name);
                  else alert("Error: " + j.error);
              })
              .catch(function(err) { alert("Upload failed: " + err); });
        };
        reader.readAsArrayBuffer(file);
    }
});
// vim: tabstop=8 shiftwidth=4 expandtab softtabstop=4
