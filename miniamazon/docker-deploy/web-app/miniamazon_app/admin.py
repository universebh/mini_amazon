from django.contrib import admin
from .models import CreditCard, DeliveryAddress, MyUser, Order, WareHouse, Product, LocalStorage, Cart, OrderCollection
# Register your models here.
admin.site.register(CreditCard)
admin.site.register(DeliveryAddress)
admin.site.register(MyUser)
admin.site.register(Order)
admin.site.register(WareHouse)
admin.site.register(Product)
admin.site.register(LocalStorage)
admin.site.register(Cart)
admin.site.register(OrderCollection)