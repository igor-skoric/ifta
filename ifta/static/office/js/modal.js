export const seatData = {
  svg_id: "seat_DISP_06_02",
  label: "DISP-06-02",
  dept: "DISP",
  zone: "06",
  seat_no: "02",
  is_active: true,
  assignment: {
    start_at: "2026-02-20T15:25:10+00:00",
    note: "",
  },
  employee: {
    id: 1,
    alias: "Andy Gordon",
    name: "Bojan Skoric",
    email: "bojan2160@gmail.com",
    phone: "051351234",
    is_active: true,
    assets: [
      {
        id: 1,
        type: "DESKTOP",
        brand: "HP",
        model: "HP",
        serial_number: "111",
        inventory_tag: "",
        status: "IN_USE",
      },
    ],
  },
};


export function createSeatModal() {
  const modal = document.getElementById("seat-dialog");
  const overlay = document.getElementById("seat-modal-overlay");

  // Seat header
  const title = document.getElementById("dlg-title");
  const seatId = document.getElementById("dlg-seat-id");
  const miDept = document.getElementById("dlg-dept");
  const miZone = document.getElementById("dlg-zone");
  const miSeatNo = document.getElementById("dlg-seatno");
  const miStatus = document.getElementById("dlg-status-pill");

  // Employee block (mora da postoji u HTML-u)
  const empName = document.getElementById("emp-name");
  const empAlias = document.getElementById("emp-alias");
  const empEmail = document.getElementById("emp-email");
  const empPhone = document.getElementById("emp-phone");
  const empActivePill = document.getElementById("emp-active-pill");

  // Assignment block
  const asStart = document.getElementById("as-start");
  const asNote = document.getElementById("as-note");

  // Assets
  const assetsBody = document.getElementById("assets-body");
  const assetsEmpty = document.getElementById("assets-empty");
  const assetsCount = document.getElementById("assets-count");

  function open() {
    modal.classList.remove("hidden");
  }

  function close() {
    modal.classList.add("hidden");
    document.body.classList.remove("overflow-hidden");
  }

  function setLoading(svgId) {
    title.textContent = "Loading...";
    seatId.textContent = svgId;

    miDept.textContent = "-";
    miZone.textContent = "-";
    miSeatNo.textContent = "-";
    miStatus.textContent = "—";

    // employee placeholders
    if (empName) empName.textContent = "-";
    if (empAlias) empAlias.textContent = "-";
    if (empEmail) empEmail.textContent = "-";
    if (empPhone) empPhone.textContent = "-";

    if (asStart) asStart.textContent = "-";
    if (asNote) asNote.textContent = "—";

    if (assetsBody) assetsBody.innerHTML = "";
    if (assetsEmpty) assetsEmpty.classList.remove("hidden");
    if (assetsCount) assetsCount.textContent = "0 items";
  }

  function formatDate(iso) {
    if (!iso) return "—";
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return iso; // fallback
    return d.toLocaleString(); // lokalno
  }

  function renderAssets(assets = []) {
    if (!assetsBody || !assetsEmpty || !assetsCount) return;

    assetsCount.textContent = `${assets.length} item${assets.length === 1 ? "" : "s"}`;

    if (!assets.length) {
      assetsBody.innerHTML = "";
      assetsEmpty.classList.remove("hidden");
      return;
    }

    assetsEmpty.classList.add("hidden");

    assetsBody.innerHTML = assets.map(a => {
      const brandModel = [a.brand, a.model].filter(Boolean).join(" / ") || "—";
      const serial = a.serial_number || "—";
      const tag = a.inventory_tag || "—";

      return `
        <tr>
          <td class="px-4 py-3">
            <span class="inline-flex items-center rounded-full bg-gray-100 px-2 py-1 text-xs border border-gray-200">${a.type}</span>
          </td>
          <td class="px-4 py-3 text-gray-800">${brandModel}</td>
          <td class="px-4 py-3 text-gray-600">${serial}</td>
          <td class="px-4 py-3 text-gray-600">${tag}</td>
          <td class="px-4 py-3 text-right">
            <span class="inline-flex items-center rounded-full bg-gray-100 text-gray-700 px-2 py-1 text-xs border border-gray-200">${a.status}</span>
          </td>
        </tr>
      `;
    }).join("");
  }

  function render(data) {
    const emp = data?.employee || null;
    const asg = data?.assignment || null;

    // header
    title.textContent = emp?.alias || data?.label || data?.svg_id || "Seat";
    seatId.textContent = data?.svg_id || "-";

    miDept.textContent = data?.dept || "-";
    miZone.textContent = data?.zone || "-";
    miSeatNo.textContent = data?.seat_no || "-";
    miStatus.textContent = data?.is_active ? "Active" : "Inactive";

    // employee
    if (empName) empName.textContent = emp?.name || "—";
    if (empAlias) empAlias.textContent = emp?.alias || "—";
    if (empEmail) empEmail.textContent = emp?.email || "—";
    if (empPhone) empPhone.textContent = emp?.phone || "—";

    if (empActivePill) {
      empActivePill.textContent = emp?.is_active ? "Employee active" : "Employee inactive";
      empActivePill.className =
        "shrink-0 inline-flex items-center rounded-full px-2 py-1 border text-xs " +
        (emp?.is_active
          ? "bg-emerald-50 text-emerald-700 border-emerald-200"
          : "bg-gray-100 text-gray-700 border-gray-200");
    }

    // assignment
    if (asStart) asStart.textContent = formatDate(asg?.start_at);
    if (asNote) asNote.textContent = asg?.note?.trim() ? asg.note : "—";

    // assets
    renderAssets(emp?.assets || []);
  }

  // close interactions
  if (overlay) overlay.addEventListener("click", close);

  document.querySelectorAll(".seat-modal-close")
    .forEach(btn => btn.addEventListener("click", close));

  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && !modal.classList.contains("hidden")) close();
  });

  return { open, close, render, setLoading };
}
