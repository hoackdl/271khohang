document.addEventListener('DOMContentLoaded', function() {
  const invoiceDataScript = document.getElementById('invoice_data');
  const itemsDataScript = document.getElementById('items_data');

  if (invoiceDataScript && itemsDataScript) {
    const invoiceData = JSON.parse(invoiceDataScript.textContent);
    const itemsData = JSON.parse(itemsDataScript.textContent);

    console.log(invoiceData);
    console.log(itemsData);

    // Gán giá trị cho input ẩn (form)
    const invoiceInput = document.getElementById('invoice_data_input');
    const itemsInput = document.getElementById('items_data_input');

    if (invoiceInput && itemsInput) {
      invoiceInput.value = JSON.stringify(invoiceData);
      itemsInput.value = JSON.stringify(itemsData);
    }
  }
});
