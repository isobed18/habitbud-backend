from django.contrib import admin
from .models import CustomUser, AvatarModel, Block, DeviceToken

admin.site.register(CustomUser)
admin.site.register(Block)
admin.site.register(DeviceToken)


@admin.register(AvatarModel)
class AvatarModelAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'emoji', 'scale', 'is_active', 'sort_order')
    list_editable = ('scale', 'is_active', 'sort_order')
    prepopulated_fields = {'slug': ('name',)}
