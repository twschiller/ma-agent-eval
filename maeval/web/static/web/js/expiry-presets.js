// Expiry quick-fill: inject preset buttons next to the date input. Progressive
// enhancement — without JS the plain date picker still works.
(function () {
  var input = document.getElementById("id_expires_at");
  var tpl = document.getElementById("expiry-presets");
  if (!input || !tpl) return;
  var presets = tpl.content.firstElementChild.cloneNode(true);
  input.insertAdjacentElement("afterend", presets);
  presets.addEventListener("click", function (event) {
    var btn = event.target.closest("[data-expiry-days]");
    if (!btn) return;
    var date = new Date();
    date.setDate(date.getDate() + Number(btn.dataset.expiryDays));
    // `type="date"` wants a local YYYY-MM-DD; build it from local parts so the
    // day doesn't shift across the UTC boundary the way toISOString() would.
    var month = String(date.getMonth() + 1).padStart(2, "0");
    var day = String(date.getDate()).padStart(2, "0");
    input.value = date.getFullYear() + "-" + month + "-" + day;
  });
})();
