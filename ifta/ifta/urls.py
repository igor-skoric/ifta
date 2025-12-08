from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views


class AdminLoginView(auth_views.LoginView):
    def get_success_url(self):
        return '/'


urlpatterns = [
    path('admin/login/', AdminLoginView.as_view(), name='admin_login'),
    path('admin/', admin.site.urls),
    path('', include('app.urls')),
]


