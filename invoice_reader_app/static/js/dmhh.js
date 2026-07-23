function initSkuAutocomplete(input) {
    let timeout = null;

    const box = document.createElement("div");
    box.className = "autocomplete-box list-group";
    box.style.position = "absolute";
    box.style.zIndex = "2000";
    input.parentNode.style.position = "relative";
    input.parentNode.appendChild(box);

    input.addEventListener("input", function () {
        clearTimeout(timeout);

        const q = this.value.trim();
        if (!q) {
            box.innerHTML = "";
            return;
        }

        timeout = setTimeout(async () => {
            const res = await fetch(`/invoice/api/products-autocomplete/?q=${encodeURIComponent(q)}`);
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
                div.textContent = `${item.sku} — ${item.ten_hang} (${item.ten_goi_chung})`;

                div.addEventListener("click", () => {
                    input.value = item.sku;

                    const row = input.closest(".po-item");
                    if (row) {
                        const tenGoiChung = row.querySelector(".ten-goi-chung-input");
                        if (tenGoiChung) tenGoiChung.value = item.ten_goi_chung;
                    }

                    box.innerHTML = "";
                });

                box.appendChild(div);
            });

        }, 300);

    });

    input.addEventListener("blur", () => {
        setTimeout(() => box.innerHTML = "", 200);
    });
}


document.addEventListener("DOMContentLoaded", function () {
    // Khởi động cho tất cả input có sẵn
    document.querySelectorAll(".sku-input").forEach(initSkuAutocomplete);
});
