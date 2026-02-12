from django.urls import path
from django.contrib.auth.views import LoginView, LogoutView
from invoice_reader_app.view import set_fiscal_year
# -------------------------
# Invoice Upload / Management
# -------------------------
from invoice_reader_app.upload_invoice import (
    upload_invoice, save_invoice, invoice_list, delete_invoice, delete_selected_invoices
)
from invoice_reader_app.multiple_invoices import (
    upload_invoices, save_multiple_invoices, invoice_summary, invoice_summary_export_excel
)
from invoice_reader_app.edit_invoice import edit_invoice
from invoice_reader_app.invoice_export_list import (
    invoice_export_list, export_invoices_excel, export_export_orders_excel
)

# -------------------------
# Suppliers & Products
# -------------------------
from invoice_reader_app.suppliers_products_view import (
    suppliers_view, supplier_add, supplier_edit, supplier_delete, supplier_detail_view
)
from invoice_reader_app.products import products_view, export_products_excel, import_products_excel
from invoice_reader_app.products_edit_view import products_edit_view
from invoice_reader_app.products_dmhh import (
    product_dmhh, products_export_excel, products_import_excel, delete_all_products, add_product, edit_product_dmhh
)
from invoice_reader_app.product_names_list import (
    product_names_list, product_names_import_excel, product_names_export_excel, product_names_edit
)

# -------------------------
# Customers
# -------------------------
from invoice_reader_app.customer_view import (
    customers_view, customer_add, customer_edit, customer_delete, customer_detail, customer_opening_balance
)
from invoice_reader_app.customer_products import (
    customer_products, customer_products_name, customer_products_name_import_excel,
    customer_product_names_export_excel, customer_products_name_edit,
    customer_product_name_delete, customer_product_name_delete_all
)

# -------------------------
# Purchase Orders & Export Orders
# -------------------------
from invoice_reader_app.purchase_oder import (
    open_or_create_po, edit_purchase_order, create_selected_invoices, purchase_order_list
)
from invoice_reader_app.export_order import (
    export_order_list, delete_selected_export_orders, delete_export_order,
    generate_po_from_invoice, export_order_detail, save_po_sku,
    create_export_order_view, delete_all_px
)

# -------------------------
# Bank Payments
# -------------------------
from invoice_reader_app.upload_bank_payments import (
    bank_payments_manage, bank_payment_detail, find_po_by_mst_invoice, bank_payment_credit
)
from invoice_reader_app.payment_list import payment_list

# -------------------------
# Inventory / Summary
# -------------------------
from invoice_reader_app.inventory_summary import inventory_summary, inventory_summary_export

# -------------------------
# API / Autocomplete
# -------------------------
from .products_autocomplete import products_autocomplete, customers_autocomplete
from .api_find_po import api_find_po, get_or_create_customer_by_mst, api_inventory_by_sku, api_products_search



from .create_export_invoice import create_export_invoice, export_invoice_detail, export_invoice_waiting_list, export_invoice_mark_done, export_invoice_bulk_delete
from .export_export_invoice_excel import export_export_invoice_excel


urlpatterns = [
    # -------------------------
    # Auth
    # -------------------------
    path('login/', LoginView.as_view(template_name='login.html'), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),


    path("set-year/<int:year>/", set_fiscal_year, name="set_fiscal_year"),
    # -------------------------
    # Invoice Upload / Management
    # -------------------------
    path('upload/', upload_invoice, name='upload_invoice'),
    path('save/', save_invoice, name='save_invoice'),
    path('list/', invoice_list, name='invoice_list'),
    path('delete/<int:invoice_id>/', delete_invoice, name='delete_invoice'),
    path('delete-selected-invoices/', delete_selected_invoices, name='delete_selected_invoices'),

    path('uploads/', upload_invoices, name='upload_invoices'),
    path('save-multiple/', save_multiple_invoices, name='save_multiple_invoices'),
    path('edit/<int:invoice_id>/', edit_invoice, name='edit_invoice'),

    path('summary/', invoice_summary, name='invoice_summary'),
    path('summary/export_excel/', invoice_summary_export_excel, name='invoice_summary_export_excel'),

    path('export/', invoice_export_list, name='invoice_export_list'),
    path('invoice/export/excel/', export_invoices_excel, name='export_invoices_excel'),
    path('export_orders/export_excel/', export_export_orders_excel, name='export_export_orders_excel'),
    path('invoice/<int:invoice_id>/po/open-or-create/', open_or_create_po, name='open_or_create_po'),

    
    # -------------------------
    # Suppliers
    # -------------------------
    path('suppliers/', suppliers_view, name='suppliers'),
    path('supplier/add/', supplier_add, name='supplier_add'),
    path('supplier/<int:supplier_id>/edit/', supplier_edit, name='supplier_edit'),
    path('supplier/<int:supplier_id>/delete/', supplier_delete, name='supplier_delete'),
    path("suppliers/<int:id>/", supplier_detail_view, name="supplier_detail"),

    # -------------------------
    # Products
    # -------------------------
    path('products/', products_view, name='products'),
    path('products/add/', add_product, name='add_product'),
    path('products/edit/<int:product_id>/', edit_product_dmhh, name='edit_product_dmhh'),
    path('products/export_excel/', export_products_excel, name='products_export_excel'),
    path('products/import_excel/', import_products_excel, name='products_import_excel'),

    # DMHH
    path('dmhh/', product_dmhh, name='product_dmhh'),
    path('dmhh/import_excel/', products_import_excel, name='dmhh_import_excel'),
    path('dmhh/export_excel/', products_export_excel, name='dmhh_export_excel'),
    path('dmhh/delete_all/', delete_all_products, name='dmhh_delete_all'),

    # Product Names
    path("product-names/", product_names_list, name="product_names_list"),
    path("product-names/import/", product_names_import_excel, name="product_names_import_excel"),
    path("product-names/export/", product_names_export_excel, name="product_names_export_excel"),
    path("product-names/<int:pk>/edit/", product_names_edit, name="product_names_edit"),
    path('products_edit/<path:ten_hang>/', products_edit_view, name='products_edit'),

    # -------------------------
    # Customers
    # -------------------------
    path('customers/', customers_view, name='customers'),
    path('customers/opening_balance/', customer_opening_balance, name='customer_opening_balance'),
    path('customer/add/', customer_add, name='customer_add'),
    path('invoice/customer/<int:pk>/edit/', customer_edit, name='customer_edit'),
    path('invoice/customer/<int:pk>/delete/', customer_delete, name='customer_delete'),
    path("customers/<int:pk>/detail/", customer_detail, name="customer_detail"),

    path('customer-products-name/', customer_products_name, name='customer_products_name'),
    path('customer-products-name/import/', customer_products_name_import_excel, name='customer_product_names_import_excel'),
    path("customer-products-name/export/", customer_product_names_export_excel, name="customer_product_names_export_excel"),
    path("customer-products-name/<int:pk>/edit/", customer_products_name_edit, name="customer_products_name_edit"),
    path("customer-products-name/<int:pk>/delete/", customer_product_name_delete, name="customer_product_name_delete"),
    path('customer-products-name/delete-all/', customer_product_name_delete_all, name='customer_product_name_delete_all'),

    path('customer-products/', customer_products, name='customer_products'),

    # -------------------------
    # Purchase Orders
    # -------------------------
    path('purchase-orders/', purchase_order_list, name='purchase_order_list'),
    path('purchase-orders/delete_all_px/', delete_all_px, name='delete_all_px'),
    path('invoices/create-selected/', create_selected_invoices, name='create_selected_invoices'),
    path('purchase-order/<int:po_id>/edit/', edit_purchase_order, name='edit_purchase_order'),
    path('purchase-order/<int:po_id>/', edit_purchase_order, name='purchase_order_detail'),

    # -------------------------
    # Export Orders
    # -------------------------
    path('export/orders/', export_order_list, name='export_order_list'),
    path('export/orders/delete_selected/', delete_selected_export_orders, name='delete_selected_export_orders'),
    path('export/orders/<int:po_id>/delete/', delete_export_order, name='delete_export_order'),
    path('export/create/', create_export_order_view, name='create_export_order'),
    path("po/<int:po_id>/save-sku/", save_po_sku, name="save_po_sku"),
    path('invoice/export/generate_po/', generate_po_from_invoice, name='generate_po_from_invoice'),
    path('export/orders/<int:po_id>/detail/', export_order_detail, name='export_order_detail'),

    # -------------------------
    # Bank Payments
    # -------------------------
    path('bank_payments_manage/', bank_payments_manage, name='bank_payments_manage'),
    path('bank_payment/<int:pk>/', bank_payment_detail, name='bank_payment_detail'),
    path("bank-payment/credit/<int:pk>/", bank_payment_credit, name="bank_payment_credit"),
    path('payments/', payment_list, name='payment_list'),
    path('invoice/api/find-po-by-mst-invoice/', find_po_by_mst_invoice, name="find_po_by_mst_invoice"),

    # -------------------------
    # Inventory / Summary
    # -------------------------
    path('summary/inventory/', inventory_summary, name='inventory_summary'),
    path('summary/inventory/export/', inventory_summary_export, name='inventory_summary_export'),

    # -------------------------
    # API / Autocomplete
    # -------------------------
    path("api/products-autocomplete/", products_autocomplete, name="products_autocomplete"),
    path("api/customers-autocomplete/", customers_autocomplete, name="customers_autocomplete"),
    path("api/find-po/", api_find_po, name="api_find_po"),
    path("api/customer-by-mst/",get_or_create_customer_by_mst,name="customer_by_mst"),
    path("api/inventory-by-sku/",api_inventory_by_sku,name="api_inventory_by_sku"),
    path("api/products-search/", api_products_search, name="products_search"),



    path("invoice/xuat/create/", create_export_invoice, name="create_export_invoice"),
    path("invoice/<int:pk>/", export_invoice_detail, name="export_invoice_detail"),
    
    path("export/<int:pk>/excel/",export_export_invoice_excel,name="export_export_invoice_excel"),
    path("invoice/waiting/",export_invoice_waiting_list,name="export_invoice_waiting_list"),
    path("invoice/<int:pk>/mark-done/",export_invoice_mark_done,name="export_invoice_mark_done"),
    path("invoice/export/bulk-delete/",export_invoice_bulk_delete,name="export_invoice_bulk_delete"),



]
