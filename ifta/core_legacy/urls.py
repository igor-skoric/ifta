from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from django.views.generic import RedirectView


class AdminLoginView(auth_views.LoginView):
    def get_success_url(self):
        return '/'


urlpatterns = [
    path('', RedirectView.as_view(url='/ifta/', permanent=False)),
    path('ifta/', include(('app.urls', 'ifta'), namespace='ifta')),
    path('statistics/', include(('app.statistics_urls', 'statistics'), namespace='statistics')),
    path('admin/login/', AdminLoginView.as_view(), name='admin_login'),
    path('admin/', admin.site.urls),
    path('api/statistic/', include('statistic.urls')),
    path('office/', include(('office.urls', 'office'), namespace='office')),
]


