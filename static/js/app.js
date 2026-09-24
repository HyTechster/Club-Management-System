// Stop double taps from sending a form twice (check-in, sign-up).
document.addEventListener("submit", (e) => {
  const btn = e.target.querySelector("button[type=submit][data-busy]");
  if (!btn) return;
  btn.disabled = true;
  btn.textContent = btn.dataset.busy;
});
