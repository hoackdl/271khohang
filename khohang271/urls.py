


from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import redirect

def redirect_to_upload(request):
    return redirect('/invoice/list/')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', redirect_to_upload),  # 👈 handles the root URL
    path('invoice/', include('invoice_reader_app.urls')),
    


]


if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)