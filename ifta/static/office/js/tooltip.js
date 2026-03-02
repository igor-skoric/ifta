export function createTooltip() {
  const tooltip = document.getElementById("seat-tooltip");
  const ttTitle = document.getElementById("tt-title");
  const ttSub = document.getElementById("tt-sub");
  const ttDept = document.getElementById("tt-dept");
  const ttZone = document.getElementById("tt-zone");
  const ttStatus = document.getElementById("tt-status");

  let lastMove = 0;

  function show(seat) {
    if (!seat) return;
    ttTitle.textContent = seat.label || seat.svg_id;
    ttSub.textContent = `ID: ${seat.svg_id}`;
    ttDept.textContent = seat.dept || "-";
    ttZone.textContent = seat.zone || "-";
    ttStatus.textContent = seat.is_active ? "Active" : "Inactive";
    tooltip.classList.remove("hidden");
  }

  function hide() {
    tooltip.classList.add("hidden");
  }

  function move(clientX, clientY) {
    // throttle
    const now = performance.now();
    if (now - lastMove < 8) return;
    lastMove = now;

    const offset = 14;
    tooltip.style.left = clientX + offset + "px";
    tooltip.style.top = clientY + offset + "px";

    // prevent overflow
    const rect = tooltip.getBoundingClientRect();
    const pad = 8;

    if (rect.right > window.innerWidth - pad) {
      tooltip.style.left = (clientX - rect.width - offset) + "px";
    }
    if (rect.bottom > window.innerHeight - pad) {
      tooltip.style.top = (clientY - rect.height - offset) + "px";
    }
  }

  return { show, hide, move };
}
