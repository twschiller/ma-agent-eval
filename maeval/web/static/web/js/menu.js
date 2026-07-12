// Close any open account menu when clicking away or pressing Escape.
document.addEventListener("click", (event) => {
  document.querySelectorAll("details[data-menu][open]").forEach((menu) => {
    if (!menu.contains(event.target)) {
      menu.open = false;
    }
  });
});
document.addEventListener("keydown", (event) => {
  if (event.key !== "Escape") {
    return;
  }
  document.querySelectorAll("details[data-menu][open]").forEach((menu) => {
    menu.open = false;
  });
});
