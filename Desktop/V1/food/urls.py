from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('', views.homepage, name='homepage'),
    path('order_page/<str:order_id>/', views.order_page, name='order_page'),
    path('order/<str:order_id>/submit/', views.submit_order, name='submit_order'),
    path('order_status/<str:order_id>/', views.order_status, name='order_status'),
    path('change_package/<str:order_id>/', views.change_package, name='change_package'),
    path('order/<str:order_id>/submit/', views.submit_order, name='submit_order'),
    path('kitchen_orders/', views.kitchen_orders, name='kitchen_orders'),
    path('checkout/<str:order_id>/', views.checkout, name='checkout'),
    #path('staff/', views.staff, name='dashboard-staff'),
    #path('product/', views.product, name='dashboard-product'),
    #path('order/', views.order, name='dashboard-order'),
]
if settings.DEBUG:  # Serve media files only in debug mode
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)