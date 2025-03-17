from django.contrib import admin
from .models import Dish, Table, Order, OrderItem, Invoice
# Register your models here.
admin.site.register(Dish)
admin.site.register(Table)
admin.site.register(OrderItem)
admin.site.register(Order)
admin.site.register(Invoice)