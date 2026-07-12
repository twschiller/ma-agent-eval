// Progressive enhancement: without JS the key is still selectable text.
document.querySelectorAll("[data-copy-target]").forEach((btn) => {
  btn.addEventListener("click", () => {
    var value = document.getElementById(btn.dataset.copyTarget).textContent;
    navigator.clipboard.writeText(value).then(() => {
      var previous = btn.textContent;
      btn.textContent = "Copied";
      setTimeout(() => {
        btn.textContent = previous;
      }, 1500);
    });
  });
});
