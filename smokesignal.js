window.addEventListener("load", function() {
    var qrcodeElement = document.getElementById("qrcode");
    var qrcode = new QRCode(qrcodeElement, {
        width: qrcodeElement.offsetWidth,
        height: qrcodeElement.offsetHeight,
        correctLevel: QRCode.CorrectLevel.L
    });
    var lastQrData = null;

    /* Scanner setup */
    var resultContainer = document.getElementById("scan-results");
    var lastResult = null;

    function onScanSuccess(decodedText, decodedResult) {
        console.debug("onScanSuccess() called");
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
    qrcode.makeCode("Smokesignal transceiving...");
    document.getElementById("phone-lower").appendChild(document.getElementById("phone-upper").firstChild);
});
// vim: tabstop=8 shiftwidth=4 expandtab softtabstop=4
