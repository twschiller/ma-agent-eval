// Progressive enhancement: without JS the key is still selectable text.
document.querySelectorAll("[data-copy-target]").forEach(function (btn) {
  btn.addEventListener("click", function () {
    var value = document.getElementById(btn.dataset.copyTarget).textContent;
    navigator.clipboard.writeText(value).then(function () {
      var previous = btn.textContent;
      btn.textContent = "Copied";
      setTimeout(function () { btn.textContent = previous; }, 1500);
    });
  });
});
