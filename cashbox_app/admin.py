from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import CustomUser, Address, Schedule


@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    """
    Настраивает отображение и функциональность модели Address в административной панели Django.
    """

    list_display = ("__str__", "id", "get_address_schedules")
    search_fields = ["city", "street", "home"]
    list_filter = ["city"]

    def get_address_schedules(self, obj):
        schedules = obj.address_schedules.all()
        return "\n".join(
            [
                f"{schedule.day_of_week}: {schedule.opening_time} - {schedule.closing_time}"
                for schedule in schedules
            ]
        )

    get_address_schedules.short_description = "Расписание"

    # Используем id вместо adress_id
    def get_id(self, obj):
        return obj.id

    get_id.short_description = "ID адреса"


@admin.register(Schedule)
class AddressScheduleAdmin(admin.ModelAdmin):
    """
    Настраивает отображение и функциональность модели Schedule в административной панели Django.
    """

    list_display = (
        "day_of_week",
        "formatted_opening_time",
        "formatted_closing_time",
        "get_full_address",
    )
    list_filter = ["day_of_week"]

    def formatted_opening_time(self, obj):
        return obj.opening_time.strftime("%H:%M")

    formatted_opening_time.short_description = "Время открытия"

    def formatted_closing_time(self, obj):
        return obj.closing_time.strftime("%H:%M")

    formatted_closing_time.short_description = "Время закрытия"

    def get_full_address(self, obj):
        return obj.address.__str__() if obj.address else "-"

    get_full_address.short_description = "Адрес"


# Добавить пользователя.
@admin.register(CustomUser)
class CustomUserAdmin(BaseUserAdmin):
    """
    Настраивает отображение и функциональность модели CustomUser в административной панели Django.
    """

    fieldsets = (
        (None, {"fields": ("username", "password")}),
        ("Personal info", {"fields": ("first_name", "last_name", "email")}),
        (
            "Permissions",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("username", "password1", "password2"),
            },
        ),
    )
