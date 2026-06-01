from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView
from .views import dashboard_home

urlpatterns = [
    path('', dashboard_home, name='dashboard'),
    # TV shortcuts (same views as /statistics/1/ …)
    path('1/', RedirectView.as_view(url='/statistics/1/', permanent=False)),
    path('2/', RedirectView.as_view(url='/statistics/2/', permanent=False)),
    path('3/', RedirectView.as_view(url='/statistics/3/', permanent=False)),
    path('accounts/', include(('accounts.urls', 'accounts'), namespace='accounts')),
    path('ifta/', include(('ifta.urls', 'ifta'), namespace='ifta')),
    path('statistics/', include(('ifta.statistics_urls', 'statistics'), namespace='statistics')),
    path('admin/login/', RedirectView.as_view(url='/accounts/login/', permanent=False), name='admin_login'),
    path('admin/', admin.site.urls),
    path('api/statistic/', include('statistic.urls')),
    path('office/', include(('office.urls', 'office'), namespace='office')),
    path('dispatch/', include(('dispatch.urls', 'dispatch'), namespace='dispatch')),
    path('leave/', include(('leave.urls', 'leave'), namespace='leave')),
    path('samsara/', include(('samsara.urls', 'samsara'), namespace='samsara')),
]


