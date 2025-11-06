from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path
from games import views as games_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', games_views.home, name='home'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)