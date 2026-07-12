// Confirm a form submission before it goes through. Replaces inline
// `onsubmit="return confirm(...)"`, which a strict CSP forbids (ADR-0010). The
// prompt text comes from the form's `data-confirm` attribute.
document.addEventListener("submit", (event) => {
  var form = event.target.closest("form[data-confirm]");
  if (!form) return;
  if (!window.confirm(form.dataset.confirm)) {
    event.preventDefault();
  }
});
