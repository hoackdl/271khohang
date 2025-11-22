from django.urls import path
from invoice_reader_app.upload_invoice import upload_invoice,save_invoice, invoice_list, delete_invoice, delete_selected_invoices
from invoice_reader_app.multiple_invoices import upload_invoices, save_multiple_invoices, invoice_summary, invoice_summary_export_excel
from invoice_reader_app.suppliers_products_view import suppliers_view, supplier_add, supplier_edit, supplier_delete
from invoice_reader_app.products import products_view, export_products_excel, import_products_excel
from invoice_reader_app.products_edit_view import products_edit_view
from invoice_reader_app.invoice_export_list import invoice_export_list, export_invoices_excel
from django.urls import path
from invoice_reader_app.customer_view import (
    customers_view,
    customer_add,
    customer_edit,
    customer_delete,
)
from invoice_reader_app.customer_products import customer_products, customer_products_name, customer_products_name_import_excel, customer_product_names_export_excel,customer_products_name_edit, customer_product_name_delete, customer_product_name_delete_all


from invoice_reader_app.inventory_summary import inventory_summary, inventory_summary_export

from invoice_reader_app.product_names_list import product_names_list, product_names_import_excel, product_names_export_excel, product_names_edit

from invoice_reader_app.edit_invoice import edit_invoice
from invoice_reader_app.products_dmhh import product_dmhh, products_export_excel,products_import_excel, delete_all_products,add_product, edit_product_dmhh

from .products_autocomplete import products_autocomplete, customers_autocomplete
from .purchase_oder import open_or_create_po,edit_purchase_order, create_selected_invoices, purchase_order_list
from .export_order import export_order_list, delete_selected_export_orders, delete_export_order, generate_po_from_invoice,export_order_detail, save_po_sku, create_export_order_view




urlpatterns = [
    path('upload/', upload_invoice, name='upload_invoice'),
    path('save/', save_invoice, name='save_invoice'),
    path('list/', invoice_list, name='invoice_list'),
  
    
    path('uploads/', upload_invoices, name='upload_invoices'),
    path('save-multiple/', save_multiple_invoices, name='save_multiple_invoices'),

    path('suppliers/', suppliers_view, name='suppliers'),
    path('supplier/add/', supplier_add, name='supplier_add'),
    path('supplier/<int:supplier_id>/edit/', supplier_edit, name='supplier_edit'),
    path('supplier/<int:supplier_id>/delete/', supplier_delete, name='supplier_delete'),
   
    path('export/', invoice_export_list, name='invoice_export_list'),  # <-- thêm
    path('invoice/export/generate_po/', generate_po_from_invoice, name='generate_po_from_invoice'),
    path('export/orders/<int:po_id>/detail/', export_order_detail, name='export_order_detail'),


   
    path('products_edit/<path:ten_hang>/', products_edit_view, name='products_edit'),


     
    path('delete/<int:invoice_id>/', delete_invoice, name='delete_invoice'),
    path('delete-selected-invoices/', delete_selected_invoices, name='delete_selected_invoices'),
    



    path('customers/', customers_view, name='customers'),
    path('customer/add/', customer_add, name='customer_add'),

    path('customer/', customer_products, name='customer_products'),
    path('invoice/customer/<int:pk>/edit/', customer_edit, name='customer_edit'),
    path('invoice/customer/<int:pk>/delete/', customer_delete, name='customer_delete'),




    #path('products/export/', customer_products_export, name='customer_products_export'),
    #path('customer_products_edit/<int:pk>/edit/', customer_products_edit, name='customer_products_edit'),


  

    path('customer-products-name/', customer_products_name, name='customer_products_name'),
    path('customer-products-name/import/', customer_products_name_import_excel, name='customer_product_names_import_excel'),
    path("customer-products-name/export/", customer_product_names_export_excel, name="customer_product_names_export_excel"),
    
    path("customer-products-name/<int:pk>/delete/", customer_product_name_delete, name="customer_product_name_delete"),
    path('customer-products-name/delete-all/', customer_product_name_delete_all, name='customer_product_name_delete_all'),

    path("customer-products-name/<int:pk>/edit/", customer_products_name_edit, name="customer_products_name_edit"),



    path('summary/', invoice_summary, name='invoice_summary'),
    path('summary/export_excel/',invoice_summary_export_excel, name='invoice_summary_export_excel'),
    path('edit/<int:invoice_id>/', edit_invoice, name='edit_invoice'),


    path('summary/inventory/', inventory_summary, name='inventory_summary'),
    path('summary/inventory/export/', inventory_summary_export, name='inventory_summary_export'),



    


    path("product-names/", product_names_list, name="product_names_list"),
    path("product-names/import/", product_names_import_excel, name="product_names_import_excel"),
    path("product-names/export/",product_names_export_excel, name="product_names_export_excel"),
    path("product-names/<int:pk>/edit/",product_names_edit, name="product_names_edit"),

    
    # Nhóm 1: Products
    path('products/', products_view, name='products'),
    path('products/export_excel/', export_products_excel, name='products_export_excel'),
    path('products/import_excel/', import_products_excel, name='products_import_excel'),

    # Nhóm 2: Danh mục hàng hóa (DMHH)
    path('dmhh/', product_dmhh, name='product_dmhh'),
    path('dmhh/import_excel/', products_import_excel, name='dmhh_import_excel'),
    path('dmhh/export_excel/', products_export_excel, name='dmhh_export_excel'),
    path('dmhh/delete_all/', delete_all_products, name='dmhh_delete_all'),
    path('products/add/', add_product, name='add_product'),
    path('products/edit/<int:product_id>/', edit_product_dmhh, name='edit_product_dmhh'),

    # Phiếu nhập
   
    
    
    path('invoices/create-selected/', create_selected_invoices, name='create_selected_invoices'),
    path('purchase-orders/', purchase_order_list, name='purchase_order_list'),
    path('invoice/export/excel/', export_invoices_excel, name='export_invoices_excel'),
    path('purchase-order/<int:po_id>/edit/', edit_purchase_order, name='edit_purchase_order'),
    path('invoice/<int:invoice_id>/po/open-or-create/', open_or_create_po, name='open_or_create_po'),
    # urls.py
    path('purchase-order/<int:po_id>/edit/', edit_purchase_order, name='edit_purchase_order'),
    path('purchase-order/<int:po_id>/',edit_purchase_order, name='purchase_order_detail'),

  
    # Api danh mục hàng hóa
    path("api/products-autocomplete/", products_autocomplete, name="products_autocomplete"),
    path("api/customers_autocomplete/", customers_autocomplete, name="customers_autocomplete"),
    
    
    
    # Phiếu xuất

    path('export/orders/', export_order_list, name='export_order_list'),
    path('export/orders/delete_selected/', delete_selected_export_orders, name='delete_selected_export_orders'),
    path('export/orders/<int:po_id>/delete/', delete_export_order, name='delete_export_order'),
    path("po/<int:po_id>/save-sku/", save_po_sku, name="save_po_sku"),
    path('export/create/', create_export_order_view, name='create_export_order')
    



]


