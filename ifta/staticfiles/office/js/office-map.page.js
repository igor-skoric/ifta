import { createTooltip } from "./tooltip.js";
import { createSeatModal } from "./modal.js";
import { buildSeatMap, setSeatStyle, attachSeatHandlers } from "./seats.js";

function getSeatsFromScriptTag() {
  const el = document.getElementById("seats-data");
  if (!el) return [];
  return JSON.parse(el.textContent);
}

document.addEventListener("DOMContentLoaded", () => {
  const seats = getSeatsFromScriptTag();
  const seatMap = buildSeatMap(seats);
  console.log(seats);
  const tooltip = createTooltip();
  const modal = createSeatModal();

  async function handleSeatClick(svgId) {
    console.log(svgId)
    try {
      modal.open();
      modal.setLoading(svgId);

      const data = seats.find(s => s.svg_id === svgId);
      modal.render(data);
    } catch (err) {
      console.error(err);
      console.log(err);
      // fallback minimalno
      modal.render({ svg_id: svgId, dept: "-", zone: "-", is_active: false });
    }
  }

  for (const seat of seats) {
    const el = document.getElementById(seat.svg_id);
    if (!el) continue;

    setSeatStyle(el, seat);
    attachSeatHandlers({
      el,
      seat: seatMap.get(seat.svg_id),
      tooltip,
      onClick: handleSeatClick,
    });
  }

  // sakrij tooltip na scroll svg hosta
  const svgHost = document.querySelector(".overflow-auto");
  if (svgHost) svgHost.addEventListener("scroll", tooltip.hide, { passive: true });
});
