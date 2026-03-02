export function buildSeatMap(seats) {
  return new Map(seats.map(s => [s.svg_id, s]));
}

export function setSeatStyle(el, seat) {
  el.classList.add("transition-all", "duration-150");
  el.style.opacity = seat.is_active ? "0.95" : "0.45";

  // inactive ostaje klikabilan
  el.classList.add("cursor-pointer");
}

export function attachSeatHandlers({ el, seat, tooltip, onClick }) {

  el.addEventListener("mouseenter", () => {
    el.classList.add("seat-hover");
    tooltip.show(seat);
  });

  el.addEventListener("mousemove", (e) => {
    tooltip.move(e.clientX, e.clientY);
  });

  el.addEventListener("mouseleave", () => {
    el.classList.remove("seat-hover");
    tooltip.hide();
  });

  el.addEventListener("click", () => onClick(el.id));
}
