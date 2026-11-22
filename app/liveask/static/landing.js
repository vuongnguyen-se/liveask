"use strict";
// The QR code in the projector picture is real: it opens this very site. It is drawn with the
// same vendored generator the screen view uses, as an image (no markup is ever built from text).
(function () {
  const img = document.getElementById("demo-qr");
  if (!img || typeof qrcode !== "function") return;
  try {
    const qr = qrcode(0, "M");
    qr.addData(location.origin + "/");
    qr.make();
    img.src = qr.createDataURL(6, 2);
    img.alt = "A QR code that opens this page";
  } catch (e) {
    /* the picture keeps its frame without the code */
  }
})();
