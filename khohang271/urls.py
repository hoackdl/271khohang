


from django.contrib import admin
from django.urls import path, include

from django.shortcuts import redirect

def redirect_to_upload(request):
    return redirect('/invoice/summary/inventory/')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', redirect_to_upload),  # 👈 handles the root URL
    path('invoice/', include('invoice_reader_app.urls')),
    



]
