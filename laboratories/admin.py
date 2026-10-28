from django.contrib import admin
from .models import Appointment, Category, Laboratory, Review, User


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('username', 'name', 'email', 'role', 'is_verified', 'is_active')
    search_fields = ('username', 'email', 'name')


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('category_name', 'slug')
    search_fields = ('category_name',)


@admin.register(Laboratory)
class LaboratoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'city', 'state', 'is_approved', 'created_at')
    list_filter = ('is_approved', 'city', 'state')
    search_fields = ('name', 'city', 'state')


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ('laboratory', 'full_name', 'contact_number', 'email_address', 'appointment_date', 'created_at')
    list_filter = ('appointment_date', 'laboratory')
    search_fields = ('full_name', 'contact_number', 'email_address', 'laboratory__name')


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('laboratory', 'user', 'rating', 'created_at')
    list_filter = ('rating',)
