from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path
from games import views as games_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path(
        'conta/entrar/',
        games_views.SelvaLoginView.as_view(),
        name='login',
    ),
    path('conta/sair/', games_views.SelvaLogoutView.as_view(), name='logout'),
    path('conta/cadastro/', games_views.signup, name='signup'),
    path('conta/verificar/', games_views.verify_email, name='verify_email'),
    path('comunidade/', games_views.community_portal, name='faq'),
    path('comunidade/doar/', games_views.donate, name='donate'),
    path('estudio/', games_views.home, name='home'),
    path('', games_views.signup, name='landing'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)