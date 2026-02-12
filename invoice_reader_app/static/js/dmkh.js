
document.addEventListener("DOMContentLoaded", function () {
  const mstInput = document.getElementById("mst-input");
  const khachHangInput = document.getElementById("khach-hang-input");
  const diaChiInput = document.getElementById("dia-chi-input");

  const box = document.createElement("div");
  box.className = "autocomplete-box list-group";
  box.style.position = "absolute";
  box.style.zIndex = "2000";
  mstInput.parentNode.style.position = "relative";
  mstInput.parentNode.appendChild(box);

  let timeout = null;

  mstInput.addEventListener("input", function () {
    clearTimeout(timeout);
    const q = this.value.trim();
    if (!q) {
      box.innerHTML = "";
      return;
    }

    timeout = setTimeout(async () => {
      const res = await fetch(`/invoice/api/customers_autocomplete/?q=${encodeURIComponent(q)}`);

      if (!res.ok) return;

      const data = await res.json();
      box.innerHTML = "";

      if (!data.length) {
        box.innerHTML = `<div class="list-group-item small text-muted">Không có kết quả</div>`;
        return;
      }

      data.forEach(item => {
        const div = document.createElement("div");
        div.className = "list-group-item list-group-item-action";
        div.textContent = `${item.ma_so_thue} — ${item.ten_khach_hang}`;

        div.addEventListener("click", () => {
          mstInput.value = item.ma_so_thue;
          khachHangInput.value = item.ten_khach_hang;
          diaChiInput.value = item.dia_chi;
          box.innerHTML = "";
        });

        box.appendChild(div);
      });
    }, 300);
  });

  mstInput.addEventListener("blur", () => {
    setTimeout(() => box.innerHTML = "", 200);
  });
});
