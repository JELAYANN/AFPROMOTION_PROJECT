from django.contrib import admin # type: ignore
from .models import (
    Customer,
    ProductCategory,
    Product,
    Order,
    OrderItem,
    Payment,
    CartItem
)

admin.site.register(Customer)
admin.site.register(ProductCategory)
admin.site.register(Product)
admin.site.register(Order)
admin.site.register(OrderItem)
admin.site.register(Payment)
admin.site.register(CartItem)
