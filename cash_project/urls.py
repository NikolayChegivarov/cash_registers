"""
Конфигурация URL-адреса для проекта multiplayer_mode.

Список `urlpatterns` направляет URL-адреса в представления. Для получения дополнительной информации см.
https://docs.djangoproject.com/en/5.0/topics/http/urls/.
Примеры:
Представления функций
1. Добавьте импорт: из представлений импорта my_app
2. Добавьте URL-адрес в urlpatterns: path('',views.home, name='home')
Представления на основе классов
1. Добавьте импорт: fromother_app.views import Home
2. Добавьте URL-адрес в urlpatterns: path('', Home.as_view(), name='home')
Включение другого URLconf
1. Импортируйте функцию include(): из django.urls import include, путь
2. Добавьте URL-адрес в urlpatterns: path('blog/', include('blog.urls'))"""

from django.contrib import admin
from django.urls import path
from cashbox_app.views import (
    CustomLoginView,
    AddressSelectionView,
    CashReportView,
    ReportSubmittedView,
    SupervisorView,
    CountVisitsView,
    CountVisitsBriefView,
    CountVisitsFullView,
    SupervisorCashReportView,
    CorrectedView,
    SavedView,
    ClosedView,
    ScheduleView,
    ScheduleReportView,
    SecretRoomView,
    PriceChangesView,
    HarvestView,
    HarvestPrintViews,
    HarvestAddressSchoiceViews,
    HarvestAddressViews,
    ChangedStatusView,
    CollectedMetalView,
    TheRemainsView
)

urlpatterns = [
    path("admin/", admin.site.urls),  # Страница администратора.
    path("login/", CustomLoginView.as_view(), name="login"),  # Авторизация.
    path(
        "address-selection/", AddressSelectionView.as_view(), name="address_selection"
    ),  # Выбор адреса.
    path(
        "cash-report-form/", CashReportView.as_view(), name="cash_report_form"
    ),  # Сверка кассы.
    path(
        "report-submitted/", ReportSubmittedView.as_view(), name="report_submitted"
    ),  # Основная страница сотрудника.
    path(
        "cash-report-form/corrected/", CorrectedView.as_view(), name="corrected"
    ),  # Корректировка.
    path(
        "report-submitted/saved/", SavedView.as_view(), name="saved"
    ),  # Сохраненные данные.
    path(
        "report-submitted/saved/closed/", ClosedView.as_view(), name="closed"
    ),  # Статус закрыто.
    path(
        "supervisor/", SupervisorView.as_view(), name="supervisor"
    ),  # Страница руководителя.
    path(
        "count_visits/", CountVisitsView.as_view(), name="count_visits"
    ),  # Выбор отчета "количество посещений".
    path(
        "count_visits/brief", CountVisitsBriefView.as_view(), name="count_visits_brief"
    ),  # Краткий отчет
    path(
        "count_visits/full", CountVisitsFullView.as_view(), name="count_visits_full"
    ),  # Полный отчет
    path(
        "schedule", ScheduleView.as_view(), name="schedule"
    ),  # Фильтр отчета "расписание".
    path(
        "schedule/report",
        ScheduleReportView.as_view(),
        name="schedule_report"
    ),  # Отчет "расписание".
    path(
        "cash_report/",
        SupervisorCashReportView.as_view(),
        name="supervisor_cash_report",
    ),  # Отчет "Кассы"
    path(
        "price_changes",
        PriceChangesView.as_view(),
        name="price_changes",
    ),  # Изменение цен
    path(
        "secret_room/",
        SecretRoomView.as_view(),
        name="secret_room",
    ),  # Тайная комната
    path("secret_room/collected_metal/",
         CollectedMetalView.as_view(),
         name='collected_metal'
         ),  # Посмотреть собранный металл.
    path(
        "harvest/",
        HarvestView.as_view(),
        name="harvest",
    ),  # Собрать урожай
    path(
        "harvest/views",
        HarvestPrintViews.as_view(),
        name="harvest_views",
    ),  # Собрать урожай весь
    path(
        "harvest/address",
        HarvestAddressSchoiceViews.as_view(),
        name="harvest_address",
    ),  # Страница выбора адреса
    path(
        "harvest/address/views",
        HarvestAddressViews.as_view(),
        name="harvest_address_views",
    ),  # Показывает урожай по конкретному адресу.
    path('changed-status/<int:selected_address_id>/',
         ChangedStatusView.as_view(),
         name='changed_status'),  # Показывает измененный адрес.
    path('the_remains/',
         TheRemainsView.as_view(),
         name='the_remains'),  # Показывает измененный адрес.
]
