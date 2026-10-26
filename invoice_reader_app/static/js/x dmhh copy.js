// Autocomplete danh mục hàng hoá theo sku <link rel="stylesheet" href="{% static 'css/dmhh.css' %}">



document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll(".sku-input").forEach(input => {
        let timeout = null;

        const suggestionBox = document.createElement("div");
        suggestionBox.className = "autocomplete-box list-group";
        suggestionBox.style.position = "absolute";
        suggestionBox.style.zIndex = "1000";
        input.parentNode.style.position = "relative";
        input.parentNode.appendChild(suggestionBox);

        input.addEventListener("input", function () {
            clearTimeout(timeout);
            const query = this.value.trim();
            if (!query) {
                suggestionBox.innerHTML = "";
                return;
            }

            timeout = setTimeout(async () => {
                try {
                    const res = await fetch(`/invoice/api/products-autocomplete/?q=${encodeURIComponent(query)}`);
                    if (!res.ok) return;
                    const data = await res.json();

                    suggestionBox.innerHTML = "";
                    if (data.length === 0) {
                        suggestionBox.innerHTML = `<div class="list-group-item text-muted small">Không có kết quả</div>`;
                        return;
                    }

                    data.forEach(item => {
                        const div = document.createElement("div");
                        div.className = "list-group-item list-group-item-action";
                        div.textContent = `${item.sku} — ${item.ten_hang} (${item.ten_goi_chung})`;

                        div.addEventListener("click", () => {
                            input.value = item.sku;

                            const row = input.closest("tr");
                            const tenGoiChungInput = row.querySelector(".ten-goi-chung-input");
                            const productNameInput = row.querySelector(".product-name-input");

                            if (tenGoiChungInput) tenGoiChungInput.value = item.ten_goi_chung;
                            if (productNameInput) productNameInput.value = item.ten_hang;

                            suggestionBox.innerHTML = "";
                        });

                        suggestionBox.appendChild(div);
                    });
                } catch (err) {
                    console.error("Lỗi autocomplete:", err);
                }
            }, 300);
        });

        input.addEventListener("blur", () => {
            setTimeout(() => (suggestionBox.innerHTML = ""), 200);
        });
    });
});

