from django.db import models
from django.contrib.auth.models import User, AbstractUser
# credit card model
from creditcards.models import CardNumberField, CardExpiryField, SecurityCodeField
from django.core.validators import MinValueValidator
from django.utils.translation import ugettext_lazy as _
# import string
# import random

class CreditCard(models.Model):
    # first parameter: actual value to be set on the model
    # second parameter: human readable name
    cc_type = models.CharField(max_length=256, verbose_name="Credit Card Type", choices=[("Master", "Master"), ("Visa", "Visa")], default="Master")
    cc_number = CardNumberField(_('card number'))
    cc_expiry = CardExpiryField(_('expiration date'))
    cc_code = SecurityCodeField(_('security code'))

    # class Meta:
    #     managed = True
    #     db_table = 'credit_card'

class DeliveryAddress(models.Model):
    x = models.IntegerField(verbose_name='X Coordinate of Delivery Address', default=0)
    y = models.IntegerField(verbose_name='Y Coordinate of Delivery Address', default=0)

    # class Meta:
    #     managed = True
    #     db_table = 'delivery_address'

class MyUser(AbstractUser):
#class MyUser(models.Model):
    #user = models.OneToOneField(User, on_delete=models.PROTECT, related_name='myuser', blank=True, null=True)
    credit_card = models.OneToOneField('CreditCard', on_delete=models.SET_NULL, related_name="myuser", blank=True, null=True)
    delivery_address = models.OneToOneField('DeliveryAddress', on_delete=models.SET_NULL, related_name="myuser", blank=True, null=True)

    # class Meta:
    #     managed = True
    #     db_table = 'my_user'

class Order(models.Model):
    order_id = models.AutoField(primary_key=True)
    #status = models.CharField(max_length = 256, default="")
    owner = models.ForeignKey('MyUser', on_delete=models.CASCADE, related_name='order', blank = True, null = True)
    warehouse = models.ManyToManyField('WareHouse', related_name='warehouse_order')
    amount = models.IntegerField(verbose_name='Amount', default=0)
    order_collection = models.ForeignKey('OrderCollection', on_delete=models.CASCADE, related_name='order', blank = True, null = True)

    # class Meta:
    #     managed = True
    #     db_table = 'order'

class OrderCollection(models.Model):
    order_collection_id = models.AutoField(primary_key=True)
    status = models.CharField(max_length = 256, default="")
    truck_id = models.IntegerField(verbose_name='Truck ID', null=True)
    owner = models.ForeignKey('MyUser', on_delete=models.CASCADE, related_name='ordercollection', blank = True, null = True)

class WareHouse(models.Model):
    warehouse_id = models.AutoField(primary_key=True)
    x = models.IntegerField(verbose_name='X Coordinate of Ware House', default=0)
    y = models.IntegerField(verbose_name='Y Coordinate of Ware House', default=0)

    # class Meta:
    #     managed = True
    #     db_table = 'ware_house'

class Product(models.Model):
    product_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length = 256, verbose_name="Product Name", choices=[("apple", "apple"), ("orange", "orange"), ("banana", "banana"), ("strawberry", "strawberry"), ("pineapple", "pineapple")], default="apple")
    description = models.TextField(verbose_name='Description', blank = True)
    price = models.FloatField(null = True, blank = True, default = 0)
    storage = models.IntegerField(verbose_name='Storage', default=0, validators=[MinValueValidator(0)])
    order = models.ManyToManyField('Order', null=True, blank=True, related_name='order')
    warehouse = models.ManyToManyField('WareHouse', related_name='warehouse')

    # class Meta:
    #     managed = True
    #     db_table = 'product'

class LocalStorage(models.Model):
    local_storage_id = models.AutoField(primary_key=True)
    product = models.ManyToManyField('Product', related_name='product_local')
    warehouse = models.ForeignKey('WareHouse', on_delete=models.CASCADE, related_name='localstorage', blank = True, null = True)
    storage = models.IntegerField(verbose_name='Storage', default=0)


class Cart(models.Model):
    cart_id = models.AutoField(primary_key=True)
    product = models.ManyToManyField('Product', related_name='product_cart')
    order = models.OneToOneField('Order', on_delete=models.CASCADE, related_name="cart", blank=True, null=True)
    amount = models.IntegerField(verbose_name='Amount', default=0, validators=[MinValueValidator(0)])
    warehouse = models.ManyToManyField('WareHouse', related_name='warehouse_cart')
    owner = models.ForeignKey('MyUser', on_delete=models.CASCADE, related_name='owner_cart', blank = True, null = True)