from django.urls import path
from . import views
from .views import CartDeleteView

urlpatterns = [
    path('home/', views.miniamazonhome, name='amazon-home'),
    path('about/', views.about, name='amazon-about'),
    path('register/', views.register, name='amazon-register'),
    path('home/products/<int:product_id>/', views.ProductDetailView, name='product-detail'),
    path('home/products/<int:product_id>/<int:warehouse_id>/amount/', views.ProductAmountView, name='product-amount'),
    path('home/cart/', views.CartListView, name='amazon-cart'),
    path('home/cart/processing/', views.OrderProcessView, name='amazon-orderprocess'),
    path('home/orderhistory/', views.OrderListView, name='order-history'),
    path('home/deliveryaddr/', views.AddressView, name='delivery-addr'),
    path('home/change_deliveryaddr/', views.changeaddress, name='change-delivery-addr'),
    path('home/cart/<int:pk>/delete/', CartDeleteView.as_view(), name = 'cart-delete'),
    path('home/order/<int:pk>/', views.OrderDetailView, name='order-detail'),
]