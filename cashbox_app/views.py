from django.contrib.auth.views import LoginView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth import login, authenticate
from django.core.exceptions import ObjectDoesNotExist
from django.http import Http404
from django.shortcuts import render, redirect
from django.views import View
from django.views.generic import FormView, TemplateView
from django.views.decorators.csrf import csrf_protect
from django.utils.decorators import method_decorator
from django.utils.timezone import now
from django.utils import timezone
from django.urls import reverse_lazy, reverse
from django.db.models import Prefetch
from django.db.models import Count
from django.db.models import Max
from django.db.models.fields import CharField
from django.db.models import (
    Case,
    Value,
    When,
    Func,
    Subquery,
    OuterRef,
    F,
)
from django.db.models.functions import (
    ExtractYear,
    ExtractMonth,
    ExtractDay,
    ExtractWeekDay,
)
from cashbox_app.forms import (
    CustomAuthenticationForm,
    AddressSelectionForm,
    SavedForm,
    MultiCashReportForm,
    YearMonthForm,
    ScheduleForm,
    SecretRoomForm,
    PriceChangesForm,
)
from cashbox_app.models import (
    Address,
    CashReport,
    CashRegisterChoices,
    CashReportStatusChoices,
    CustomUser,
    Schedule,
    GoldStandard,
    SecretRoom,
)
from datetime import date
import pandas as pd
import logging
from django.db import transaction

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)

# Увеличиваем максимальное количество отображаемых столбцов в pandas
pd.set_option("display.max_columns", None)
# Увеличиваем ширину вывода в pandas
pd.set_option("display.width", 1000)


def current_balance(address_id):
    """Функция для получения текущего баланса кассы"""
    # Создаю словарь с балансами касс.
    balance = {"buying_up": None, "pawnshop": None, "technique": None}

    # BUYING_UP ORM зарос
    buying_up_reports_BUYING_UP = (
        CashReport.objects.filter(
            cas_register=CashRegisterChoices.BUYING_UP, id_address_id=address_id
        )
        .values("cash_register_end")
        .annotate(last_updated=Max("updated_at"))
        .order_by("-last_updated")
        .first()
    )

    if buying_up_reports_BUYING_UP:
        # Если результат есть, добавляю его в словарь.
        balance["buying_up"] = buying_up_reports_BUYING_UP["cash_register_end"]
        print(f"Текущий баланс BUYING_UP: {balance.get('buying_up')}")
    else:
        # Если значения нет. Устанавливаю 0
        balance["buying_up"] = 0
        print(f"Отчетов по Скупке для адреса {address_id} не найдено")

    # PAWNSHOP ORM зарос
    buying_up_reports_PAWNSHOP = (
        CashReport.objects.filter(
            cas_register=CashRegisterChoices.PAWNSHOP, id_address_id=address_id
        )
        .values("cash_register_end")
        .annotate(last_updated=Max("updated_at"))
        .order_by("-last_updated")
        .first()
    )

    if buying_up_reports_PAWNSHOP:
        balance["pawnshop"] = buying_up_reports_PAWNSHOP["cash_register_end"]
        print(f"Текущий баланс PAWNSHOP: {balance.get('pawnshop')}")
    else:
        balance["pawnshop"] = 0
        print(f"Отчетов по Ломбарду для адреса {address_id} не найдено")

    # TECHNIQUE ORM зарос
    buying_up_reports_TECHNIQUE = (
        CashReport.objects.filter(
            cas_register=CashRegisterChoices.TECHNIQUE, id_address_id=address_id
        )
        .values("cash_register_end")
        .annotate(last_updated=Max("updated_at"))
        .order_by("-last_updated")
        .first()
    )

    if buying_up_reports_TECHNIQUE:
        balance["technique"] = buying_up_reports_TECHNIQUE["cash_register_end"]
        print(f"Текущий баланс TECHNIQUE: {balance.get('technique')}")
    else:
        balance["technique"] = 0
        print(f"Отчетов по Технике для адреса {address_id} не найдено")

    return balance


class CustomLoginView(LoginView):
    """Представление для авторизации."""

    template_name = "login.html"
    form_class = CustomAuthenticationForm

    # success_url = reverse_lazy('address_selection')  # .html

    def form_valid(self, form):
        """
        Проверяет валидность формы и выполняет действия при успешной валидации.

        Этот метод вызывается после того, как форма была успешно валидирана.
        Он проверяет данные формы, выводит имя пользователя и затем передает управление родительскому классу.

        :param form: Объект формы Django, содержащий очищенные данные
        :return: True, если форма валидна, False в противном случае
        """
        username = form.cleaned_data.get("username")
        password = form.cleaned_data.get("password")

        # Authenticate the user
        user = authenticate(username=username, password=password)

        if user is not None:
            login(self.request, user)

            user_str = str(user.username)

            print(f"Вошел пользователь: {user_str}")

            if user_str == "Руководитель":
                return redirect(reverse_lazy("supervisor"))
            else:
                return redirect(reverse_lazy("address_selection"))
        else:
            # Handle invalid credentials
            print("Неверные учетные данные")
            return self.form_invalid(form)


class AddressSelectionView(FormView):
    """Представление для выбора адреса."""

    template_name = "address_selection.html"
    form_class = AddressSelectionForm
    success_url = reverse_lazy("cash_report_form")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = self.form_class()
        return context

    def form_valid(self, form):
        selected_address = form.cleaned_data["addresses"]
        self.request.session["selected_address_id"] = selected_address.id

        # Получаем текущего пользователя
        current_user = self.request.user

        # Проверяем, является ли пользователь аутентифицированным
        if current_user.is_authenticated:
            print(f"{current_user.username} выбрал адрес: {selected_address}")
        else:
            print("Ошибка: пользователь не аутентифицирован")

        return super().form_valid(form)

    def get_success_url(self):
        """Возвращает URL успешного завершения для текущего представления."""
        return self.success_url


class CashReportView(LoginRequiredMixin, FormView):
    """Страница сверки касс."""

    template_name = "cash_report_form.html"
    form_class = MultiCashReportForm

    @method_decorator(csrf_protect)
    def dispatch(self, request, *args, **kwargs):
        """Метод dispatch является отправной точкой для всех запросов в представлении класса.
        Применяя декоратор к этому методу, мы обеспечиваем, что проверка CSRF будет
        выполняться для всех типов запросов (GET, POST и т.д.)."""
        return super().dispatch(request, *args, **kwargs)

    def get_initial(self):
        """
        Функция для получения начальных значений данных формы.
        Возвращает словарь с начальными значениями полей формы,
        включая выбранный адрес и автора (текущего пользователя).
        """
        initial = {}
        selected_address_id = self.request.session.get("selected_address_id")
        if selected_address_id:
            initial["id_address"] = Address.objects.get(id=selected_address_id)
        initial["author"] = self.request.user
        return initial

    def get_form(self, form_class=None):
        """
        Конфигурирует форму, отключая поля, которые не должны быть изменены.
        """
        # Получает экземпляр формы из родительского класса
        form = super().get_form(form_class)

        # Адрес для формы из сессии пользователя.
        selected_address_id = self.request.session.get("selected_address_id")
        if selected_address_id:
            form.fields["id_address"].queryset = Address.objects.filter(
                id=selected_address_id
            )
        else:
            form.fields["id_address"].queryset = Address.objects.all()[:1]

        # Получаем актуальные балансы касс
        current_balance_ = current_balance(selected_address_id)

        # Устанавливаю значения для полей.
        form.initial["data"] = now().strftime("%Y-%m-%d")
        form.initial["cas_register_buying_up"] = CashRegisterChoices.BUYING_UP
        form.initial["cash_balance_beginning_buying_up"] = current_balance_["buying_up"]
        form.initial["cas_register_pawnshop"] = CashRegisterChoices.PAWNSHOP
        form.initial["cash_balance_beginning_pawnshop"] = current_balance_["pawnshop"]
        form.initial["cas_register_technique"] = CashRegisterChoices.TECHNIQUE
        form.initial["cash_balance_beginning_technique"] = current_balance_["technique"]

        # Отключаю поля для редактирования
        form.fields["id_address"].disabled = True
        form.fields["author"].disabled = True
        form.fields["cas_register_buying_up"].disabled = True
        form.fields["cash_balance_beginning_buying_up"].disabled = True
        form.fields["cas_register_pawnshop"].disabled = True
        form.fields["cash_balance_beginning_pawnshop"].disabled = True
        form.fields["cas_register_technique"].disabled = True
        form.fields["cash_balance_beginning_technique"].disabled = True
        form.fields["cash_register_end_buying_up"].disabled = True
        form.fields["cash_register_end_pawnshop"].disabled = True
        form.fields["cash_register_end_technique"].disabled = True

        # Запрет на редактирование статуса.
        if hasattr(form, "fields") and "status" in form.fields:
            form.fields["status"].disabled = True

        print(f"Address ID: {selected_address_id}")

        return form

    def post(self, request, *args, **kwargs):
        """
        Этот метод обрабатывает отправку формы на сервер.
        Он проверяет валидность формы, если форма валидна, то сохраняет данные и возвращает успешный ответ.
        Если форма невалидна, то выводит ошибки и возвращает ответ о некорректности данных.
        """
        form = self.get_form()
        if form.is_valid():
            print("Попытка сохранить.")
            form.save()
            return self.form_valid(form)
        else:
            print("Форма невалидна:", form.errors)
            return self.form_invalid(form)

    def get_success_url(self):
        """Возвращает URL успешного завершения для текущего представления."""

        return reverse_lazy("report_submitted")


class ReportSubmittedView(FormView):
    """
    Основная страница сотрудника.
    """

    template_name = "report_submitted.html"
    form_class = MultiCashReportForm

    @method_decorator(csrf_protect)
    def dispatch(self, request, *args, **kwargs):
        """Метод dispatch является отправной точкой для всех запросов в представлении класса.
        Применяя декоратор к этому методу, мы обеспечиваем, что проверка CSRF будет
        выполняться для всех типов запросов (GET, POST и т.д.)."""
        return super().dispatch(request, *args, **kwargs)

    def get_initial(self):
        """
        Возвращает начальные данные для формы, включая:
        - id_address: выбранный адрес из сессии пользователя, если он существует.
        - author: текущий пользователь, который отправил форму.
        """
        initial = {}
        selected_address_id = self.request.session.get("selected_address_id")
        if selected_address_id:
            initial["id_address"] = Address.objects.get(id=selected_address_id)
        initial["author"] = self.request.user

        return initial

    def get_form(self, form_class=None):
        """
        Конфигурирует форму, отключая поля, которые не должны быть изменены.
        """
        form = super().get_form(form_class)

        # Адрес для формы из сессии пользователя.
        selected_address_id = self.request.session.get("selected_address_id")
        if selected_address_id:
            form.fields["id_address"].queryset = Address.objects.filter(
                id=selected_address_id
            )
        else:
            form.fields["id_address"].queryset = Address.objects.all()[:1]

        address_id = selected_address_id

        # ПОЛУЧАЮ ДАННЫЕ ИЗ БД.
        # BUYING_UP.
        buying_up_reports_BUYING_UP = (
            CashReport.objects.filter(
                cas_register=CashRegisterChoices.BUYING_UP, id_address_id=address_id
            )
            .annotate(last_updated=Max("updated_at"))
            .order_by("-last_updated")
            .first()
        )
        # PAWNSHOP.
        buying_up_reports_PAWNSHOP = (
            CashReport.objects.filter(
                cas_register=CashRegisterChoices.PAWNSHOP, id_address_id=address_id
            )
            .annotate(last_updated=Max("updated_at"))
            .order_by("-last_updated")
            .first()
        )
        # TECHNIQUE.
        buying_up_reports_TECHNIQUE = (
            CashReport.objects.filter(
                cas_register=CashRegisterChoices.TECHNIQUE, id_address_id=address_id
            )
            .annotate(last_updated=Max("updated_at"))
            .order_by("-last_updated")
            .first()
        )

        # Устанавливаю значения для полей.
        # Общее
        form.initial["data"] = now().strftime("%Y-%m-%d")
        # BUYING_UP.
        form.initial["cas_register_buying_up"] = (
            buying_up_reports_BUYING_UP.cas_register
        )
        form.initial["cash_balance_beginning_buying_up"] = (
            buying_up_reports_BUYING_UP.cash_balance_beginning
        )
        form.initial["introduced_buying_up"] = buying_up_reports_BUYING_UP.introduced
        form.initial["interest_return_buying_up"] = (
            buying_up_reports_BUYING_UP.interest_return
        )
        form.initial["loans_issued_buying_up"] = (
            buying_up_reports_BUYING_UP.loans_issued
        )
        form.initial["used_farming_buying_up"] = (
            buying_up_reports_BUYING_UP.used_farming
        )
        form.initial["boss_took_it_buying_up"] = (
            buying_up_reports_BUYING_UP.boss_took_it
        )
        form.initial["cash_register_end_buying_up"] = (
            buying_up_reports_BUYING_UP.cash_register_end
        )
        # PAWNSHOP.
        form.initial["cas_register_pawnshop"] = buying_up_reports_PAWNSHOP.cas_register
        form.initial["cash_balance_beginning_pawnshop"] = (
            buying_up_reports_PAWNSHOP.cash_balance_beginning
        )
        form.initial["introduced_pawnshop"] = buying_up_reports_PAWNSHOP.introduced
        form.initial["interest_return_pawnshop"] = (
            buying_up_reports_PAWNSHOP.interest_return
        )
        form.initial["loans_issued_pawnshop"] = buying_up_reports_PAWNSHOP.loans_issued
        form.initial["used_farming_pawnshop"] = buying_up_reports_PAWNSHOP.used_farming
        form.initial["boss_took_it_pawnshop"] = buying_up_reports_PAWNSHOP.boss_took_it
        form.initial["cash_register_end_pawnshop"] = (
            buying_up_reports_PAWNSHOP.cash_register_end
        )
        # TECHNIQUE.
        form.initial["cas_register_technique"] = (
            buying_up_reports_TECHNIQUE.cas_register
        )
        form.initial["cash_balance_beginning_technique"] = (
            buying_up_reports_TECHNIQUE.cash_balance_beginning
        )
        form.initial["introduced_technique"] = buying_up_reports_TECHNIQUE.introduced
        form.initial["interest_return_technique"] = (
            buying_up_reports_TECHNIQUE.interest_return
        )
        form.initial["loans_issued_technique"] = (
            buying_up_reports_TECHNIQUE.loans_issued
        )
        form.initial["used_farming_technique"] = (
            buying_up_reports_TECHNIQUE.used_farming
        )
        form.initial["boss_took_it_technique"] = (
            buying_up_reports_TECHNIQUE.boss_took_it
        )
        form.initial["cash_register_end_technique"] = (
            buying_up_reports_TECHNIQUE.cash_register_end
        )

        # ОТКЛЮЧАЮ ПОЛЯ ДЛЯ РЕДАКТИРОВАНИЯ.
        form.fields["author"].disabled = True
        form.fields["id_address"].disabled = True
        form.fields["data"].disabled = True
        # BUYING_UP.
        form.fields["cas_register_buying_up"].disabled = True
        form.fields["cash_balance_beginning_buying_up"].disabled = True
        form.fields["introduced_buying_up"].disabled = True
        form.fields["interest_return_buying_up"].disabled = True
        form.fields["loans_issued_buying_up"].disabled = True
        form.fields["used_farming_buying_up"].disabled = True
        form.fields["boss_took_it_buying_up"].disabled = True
        form.fields["cash_register_end_buying_up"].disabled = True
        # PAWNSHOP.
        form.fields["cas_register_pawnshop"].disabled = True
        form.fields["cash_balance_beginning_pawnshop"].disabled = True
        form.fields["introduced_pawnshop"].disabled = True
        form.fields["interest_return_pawnshop"].disabled = True
        form.fields["loans_issued_pawnshop"].disabled = True
        form.fields["used_farming_pawnshop"].disabled = True
        form.fields["boss_took_it_pawnshop"].disabled = True
        form.fields["cash_register_end_pawnshop"].disabled = True
        # TECHNIQUE.
        form.fields["cas_register_technique"].disabled = True
        form.fields["cash_balance_beginning_technique"].disabled = True
        form.fields["introduced_technique"].disabled = True
        form.fields["interest_return_technique"].disabled = True
        form.fields["loans_issued_technique"].disabled = True
        form.fields["used_farming_technique"].disabled = True
        form.fields["boss_took_it_technique"].disabled = True
        form.fields["cash_register_end_technique"].disabled = True

        # Запрет на редактирование статуса.
        if hasattr(form, "fields") and "status" in form.fields:
            form.fields["status"].disabled = True

        return form

    def post(self, request, *args, **kwargs):

        form = self.get_form()
        if form.is_valid():
            submit_button = request.POST.get("submit_button")
            if submit_button == "Корректировать":
                # Получаем текущий отчет из базы данных по трем кассам.
                cash_report = CashReport.objects.filter(
                    id_address=self.request.session.get("selected_address_id"),
                    author=self.request.user,
                    status=CashReportStatusChoices.OPEN,
                )

                if cash_report:
                    print(f"{request.user} корректирует.")
                    return redirect(reverse_lazy("corrected"))
                else:
                    print("Нажали 'Корректировать', но отчет уже закрыт.")
                    return redirect(reverse_lazy("closed"))

            elif submit_button == "Сохранить":
                # Получаем текущий отчет из базы данных по трем кассам.
                cash_report = CashReport.objects.filter(
                    id_address=self.request.session.get("selected_address_id"),
                    author=self.request.user,
                    status=CashReportStatusChoices.OPEN,
                )

                if cash_report:
                    print("Обновляем данные в бд перед закрытием.")
                    form.save()
                    print("\nИзменяем статус на CLOSED")
                    CashReport.objects.filter(
                        id__in=cash_report.values_list("id")
                    ).update(status=CashReportStatusChoices.CLOSED)

                    return redirect(reverse_lazy("saved"))
                else:
                    # Если статус закрыто, то выводим на страницу 'closed'.
                    return redirect(reverse_lazy("closed"))

            elif submit_button == "Самоуничтожение":
                return redirect(reverse_lazy("secret_room"))

        return self.render_to_response(self.get_context_data(form=form))


class CorrectedView(FormView):
    """
    Страница корректировки собственного отчета сотрудником.
    """

    template_name = "сorrected.html"
    form_class = MultiCashReportForm

    @method_decorator(csrf_protect)
    def dispatch(self, request, *args, **kwargs):
        """
        Метод dispatch является отправной точкой для всех запросов в представлении класса.
        Применяя декоратор к этому методу, мы обеспечиваем, что проверка CSRF будет
        выполняться для всех типов запросов (GET, POST и т.д.).
        """
        return super().dispatch(request, *args, **kwargs)

    def get_initial(self):
        """
        Функция для получения начальных значений данных формы.
        Возвращает словарь с начальными значениями полей формы,
        включая выбранный адрес и автора (текущего пользователя).
        """
        initial = {}
        selected_address_id = self.request.session.get("selected_address_id")
        if selected_address_id:
            initial["id_address"] = Address.objects.get(id=selected_address_id)
        initial["author"] = self.request.user

        return initial

    def post(self, request, *args, **kwargs):
        """
        Этот метод обрабатывает отправку формы на сервер.
        Он проверяет валидность формы, если форма валидна, то сохраняет данные и возвращает успешный ответ.
        Если форма невалидна, то выводит ошибки и возвращает ответ о некорректности данных.
        """
        form = self.get_form()
        if form.is_valid():
            print(f"{request.user} сохраняет корректировку.")
            form.save()
            return self.form_valid(form)
        else:
            print("Форма невалидна:", form.errors)
            return self.form_invalid(form)

    def get_form(self, form_class=None):
        """
        Конфигурирует форму, отключая поля, которые не должны быть изменены.
        """
        # Получает экземпляр формы из родительского класса
        form = super().get_form(form_class)

        # Адрес для формы из сессии пользователя.
        selected_address_id = self.request.session.get("selected_address_id")
        if selected_address_id:
            form.fields["id_address"].queryset = Address.objects.filter(
                id=selected_address_id
            )
        else:
            form.fields["id_address"].queryset = Address.objects.all()[:1]

        address_id = selected_address_id

        # BUYING_UP ORM запрос
        buying_up_reports_BUYING_UP = (
            CashReport.objects.filter(
                cas_register=CashRegisterChoices.BUYING_UP, id_address_id=address_id
            )
            .annotate(last_updated=Max("updated_at"))
            .order_by("-last_updated")
            .first()
        )

        # PAWNSHOP ORM запрос
        buying_up_reports_PAWNSHOP = (
            CashReport.objects.filter(
                cas_register=CashRegisterChoices.PAWNSHOP, id_address_id=address_id
            )
            .annotate(last_updated=Max("updated_at"))
            .order_by("-last_updated")
            .first()
        )

        # TECHNIQUE ORM запрос
        buying_up_reports_TECHNIQUE = (
            CashReport.objects.filter(
                cas_register=CashRegisterChoices.TECHNIQUE, id_address_id=address_id
            )
            .annotate(last_updated=Max("updated_at"))
            .order_by("-last_updated")
            .first()
        )

        # Устанавливаю значения для полей.
        form.initial["data"] = now().strftime("%Y-%m-%d")

        form.initial["cas_register_buying_up"] = CashRegisterChoices.BUYING_UP
        form.initial["cash_balance_beginning_buying_up"] = (
            buying_up_reports_BUYING_UP.cash_balance_beginning
        )
        form.initial["introduced_buying_up"] = buying_up_reports_BUYING_UP.introduced
        form.initial["interest_return_buying_up"] = (
            buying_up_reports_BUYING_UP.interest_return
        )
        form.initial["loans_issued_buying_up"] = (
            buying_up_reports_BUYING_UP.loans_issued
        )
        form.initial["used_farming_buying_up"] = (
            buying_up_reports_BUYING_UP.used_farming
        )
        form.initial["boss_took_it_buying_up"] = (
            buying_up_reports_BUYING_UP.boss_took_it
        )
        form.initial["cash_register_end_buying_up"] = (
            buying_up_reports_BUYING_UP.cash_register_end
        )

        form.initial["cas_register_pawnshop"] = CashRegisterChoices.PAWNSHOP
        form.initial["cash_balance_beginning_pawnshop"] = (
            buying_up_reports_PAWNSHOP.cash_balance_beginning
        )
        form.initial["introduced_pawnshop"] = buying_up_reports_PAWNSHOP.introduced
        form.initial["interest_return_pawnshop"] = (
            buying_up_reports_PAWNSHOP.interest_return
        )
        form.initial["loans_issued_pawnshop"] = buying_up_reports_PAWNSHOP.loans_issued
        form.initial["used_farming_pawnshop"] = buying_up_reports_PAWNSHOP.used_farming
        form.initial["boss_took_it_pawnshop"] = buying_up_reports_PAWNSHOP.boss_took_it
        form.initial["cash_register_end_pawnshop"] = (
            buying_up_reports_PAWNSHOP.cash_register_end
        )

        form.initial["cas_register_technique"] = CashRegisterChoices.TECHNIQUE
        form.initial["cash_balance_beginning_technique"] = (
            buying_up_reports_TECHNIQUE.cash_balance_beginning
        )
        form.initial["introduced_technique"] = buying_up_reports_TECHNIQUE.introduced
        form.initial["interest_return_technique"] = (
            buying_up_reports_TECHNIQUE.interest_return
        )
        form.initial["loans_issued_technique"] = (
            buying_up_reports_TECHNIQUE.loans_issued
        )
        form.initial["used_farming_technique"] = (
            buying_up_reports_TECHNIQUE.used_farming
        )
        form.initial["boss_took_it_technique"] = (
            buying_up_reports_TECHNIQUE.boss_took_it
        )
        form.initial["cash_register_end_technique"] = (
            buying_up_reports_TECHNIQUE.cash_register_end
        )

        # Отключаю поля для редактирования
        form.fields["id_address"].disabled = True
        form.fields["author"].disabled = True
        form.fields["cas_register_buying_up"].disabled = True
        form.fields["cash_balance_beginning_buying_up"].disabled = True
        form.fields["cas_register_pawnshop"].disabled = True
        form.fields["cash_balance_beginning_pawnshop"].disabled = True
        form.fields["cas_register_technique"].disabled = True
        form.fields["cash_balance_beginning_technique"].disabled = True
        form.fields["cash_register_end_buying_up"].disabled = True
        form.fields["cash_register_end_pawnshop"].disabled = True
        form.fields["cash_register_end_technique"].disabled = True

        # Запрет на редактирование статуса.
        if hasattr(form, "fields") and "status" in form.fields:
            form.fields["status"].disabled = True

        return form

    def get_success_url(self):
        """Возвращает URL успешного завершения для текущего представления."""
        return reverse_lazy("report_submitted")


class SavedView(FormView):
    """
    Страница сохранения.
    """

    template_name = "report_submitted_saved.html"
    form_class = SavedForm

    @method_decorator(csrf_protect)
    def dispatch(self, request, *args, **kwargs):
        """
        Метод dispatch является отправной точкой для всех запросов в представлении класса.
        Применяя декоратор к этому методу, мы обеспечиваем, что проверка CSRF будет
        выполняться для всех типов запросов (GET, POST и т.д.).
        """
        return super().dispatch(request, *args, **kwargs)

    def get_initial(self):
        """
        Функция для получения начальных значений данных формы.
        Возвращает словарь с начальными значениями полей формы,
        включая выбранный адрес и автора (текущего пользователя).
        """
        initial = {}
        selected_address_id = self.request.session.get("selected_address_id")
        if selected_address_id:
            initial["id_address"] = Address.objects.get(id=selected_address_id)
        initial["author"] = self.request.user

        return initial

    def get_form(self, form_class=None):
        """
        Конфигурирует форму, отключая поля, которые не должны быть изменены.
        """
        # Получает экземпляр формы из родительского класса
        form = super().get_form(form_class)

        # Адрес для формы из сессии пользователя.
        selected_address_id = self.request.session.get("selected_address_id")
        if selected_address_id:
            form.fields["id_address"].queryset = Address.objects.filter(
                id=selected_address_id
            )
        else:
            form.fields["id_address"].queryset = Address.objects.all()[:1]

        address_id = selected_address_id

        # BUYING_UP ORM зарос
        buying_up_reports_BUYING_UP = (
            CashReport.objects.filter(
                cas_register=CashRegisterChoices.BUYING_UP, id_address_id=address_id
            )
            .annotate(last_updated=Max("updated_at"))
            .order_by("-last_updated")
            .first()
        )

        # PAWNSHOP ORM зарос
        buying_up_reports_PAWNSHOP = (
            CashReport.objects.filter(
                cas_register=CashRegisterChoices.PAWNSHOP, id_address_id=address_id
            )
            .annotate(last_updated=Max("updated_at"))
            .order_by("-last_updated")
            .first()
        )

        # TECHNIQUE ORM зарос
        buying_up_reports_TECHNIQUE = (
            CashReport.objects.filter(
                cas_register=CashRegisterChoices.TECHNIQUE, id_address_id=address_id
            )
            .annotate(last_updated=Max("updated_at"))
            .order_by("-last_updated")
            .first()
        )

        # Устанавливаю значения для полей.
        form.initial["data"] = now().strftime("%Y-%m-%d")

        form.initial["cas_register_buying_up"] = CashRegisterChoices.BUYING_UP
        form.initial["cash_register_end_buying_up"] = (
            buying_up_reports_BUYING_UP.cash_register_end
        )

        form.initial["cas_register_pawnshop"] = CashRegisterChoices.PAWNSHOP
        form.initial["cash_register_end_pawnshop"] = (
            buying_up_reports_PAWNSHOP.cash_register_end
        )

        form.initial["cas_register_technique"] = CashRegisterChoices.TECHNIQUE
        form.initial["cash_register_end_technique"] = (
            buying_up_reports_TECHNIQUE.cash_register_end
        )

        # Отключаю поля для редактирования
        form.fields["id_address"].disabled = True
        form.fields["author"].disabled = True
        form.fields["cas_register_buying_up"].disabled = True
        form.fields["cas_register_pawnshop"].disabled = True
        form.fields["cas_register_technique"].disabled = True
        form.fields["cash_register_end_buying_up"].disabled = True
        form.fields["cash_register_end_pawnshop"].disabled = True
        form.fields["cash_register_end_technique"].disabled = True

        # Запрет на редактирование статуса.
        if hasattr(form, "fields") and "status" in form.fields:
            form.fields["status"].disabled = True

        print(f"Selected address ID: {selected_address_id}")

        return form

    def post(self, request, *args, **kwargs):
        form = self.get_form()
        if form.is_valid():
            submit_button = request.POST.get("submit_button")
            if submit_button == "Сменить пользователя":
                return redirect(reverse_lazy("login"))
            elif submit_button == "Сменить адрес":
                return redirect(reverse_lazy("address_selection"))
            elif submit_button == "Новый день":
                return redirect(reverse_lazy("cash_report_form"))

        return self.render_to_response(self.get_context_data(form=form))


class ClosedView(View):
    """Страница указывающая на то что отчет закрыт
    и дальнейшая корректировка его не возможна."""

    template_name = "closed.html"

    def get(self, request):
        return render(request, self.template_name)


class SupervisorView(TemplateView):
    """
    Страница выбора отчета для руководителя.
    """

    template_name = "supervisor.html"


class ScheduleView(TemplateView):
    """
    Страница фильтра отчета соблюдения расписания.
    """

    template_name = "schedule.html"
    form_class = ScheduleForm

    @method_decorator(csrf_protect)
    def dispatch(self, request, *args, **kwargs):
        """
        Метод dispatch является отправной точкой для всех запросов в представлении класса.
        Применяя декоратор к этому методу, мы обеспечиваем, что проверка CSRF будет
        выполняться для всех типов запросов (GET, POST и т.д.).
        """
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["form"] = self.form_class()

    def get(self, request, *args, **kwargs):
        """
        Обработка GET-запроса
        """
        form = ScheduleForm()
        context = {"form": form}
        return self.render_to_response(context)

    def post(self, request):
        form = self.form_class(request.POST)
        if request.POST.get("action") == "Получить отчет":
            if form.is_valid():
                schedule_data = {
                    "addresses": form.cleaned_data["addresses"].id,
                    "year": form.cleaned_data["year"],
                    "month": form.cleaned_data["month"],
                }

                print("Полученные данные:", schedule_data)

                # Добавляем данные в сессию.
                request.session["schedule_form_data"] = schedule_data

                return redirect("schedule_report")


def format_date_expr(date_expr):
    """Конвертирует время в формат DATE"""
    return Func(date_expr, function="DATE", template="%(function)s(%(expressions)s)")


def format_time_expr(date_expr):
    """Конвертирует время в формат TAME"""
    return Func(
        date_expr, function="TO_CHAR", template="TO_CHAR(%(expressions)s, 'HH24:MI:SS')"
    )


class ScheduleReportView(TemplateView):
    """Отчет по соблюдению расписания.

    Attributes:
        template_name (str): Имя шаблона для отображения формы.

    Methods:
        get():
    """

    template_name = "schedule_report.html"

    def get(self, request, *args, **kwargs):
        if "schedule_form_data" in request.session:
            session_data = request.session.pop("schedule_form_data")
            print(f"schedule_data: {session_data}")
            addresses = session_data["addresses"]
            year = session_data["year"]
            month = session_data["month"]

            days_of_week = [
                "Воскресенье",
                "Понедельник",
                "Вторник",
                "Среда",
                "Четверг",
                "Пятница",
                "Суббота",
            ]

            schedule_subquery = Schedule.objects.filter(
                address_id=OuterRef("id_address"), day_of_week=F("day_of_week")
            ).values("opening_time", "closing_time")

            schedule_report = (
                CashReport.objects.filter(
                    updated_at__year=year,
                    updated_at__month=month,
                    cas_register=CashRegisterChoices.BUYING_UP,
                    id_address=addresses,
                )
                .select_related("id_address")
                .annotate(
                    shift_date_all=F("shift_date"),
                    updated_at_all=F("updated_at"),
                    date=format_date_expr("shift_date"),
                    opening_time_fact=format_time_expr("shift_date"),
                    closing_time_fact=format_time_expr("updated_at"),
                    day_number=ExtractWeekDay(F("shift_date")),
                    day_of_week=Case(
                        *[
                            When(day_number=i, then=Value(days_of_week[i - 1]))
                            for i in range(1, 8)
                        ],
                        output_field=CharField(),
                    ),
                )
                .values(
                    "id_address__street",
                    "id_address__home",
                    "shift_date_all",
                    "updated_at_all",
                    "date",
                    "opening_time_fact",
                    "closing_time_fact",
                    "author__username",
                    "day_of_week",
                )
            )

            schedule_report_with_schedule = schedule_report.annotate(
                opening_time=Subquery(schedule_subquery.values("opening_time")[:1]),
                closing_time=Subquery(schedule_subquery.values("closing_time")[:1]),
            ).order_by("date")

            print("\nSQL запрос:")
            print(schedule_report_with_schedule.query)

            df = pd.DataFrame(list(schedule_report_with_schedule))

            print("\nРезультат в формате DataFrame:")
            print(df)

            return self.render_to_response(
                {
                    "schedule_report": schedule_report_with_schedule,
                    "df": df.to_html(index=False),
                    "days_of_week": days_of_week,
                }
            )
        return render(request, self.template_name)


class CountVisitsView(TemplateView):
    """Фильтрация по дате, выбор версии отчета.

    Attributes:
        template_name (str): Имя шаблона для отображения формы.

    Methods:
        dispatch(): Метод dispatch является отправной точкой для всех запросов в представлении класса.
        Применяя декоратор к этому методу, мы обеспечиваем, что проверка CSRF будет
        выполняться для всех типов запросов (GET, POST и т.д.).
        get(): Создает экземпляр формы YearMonthForm и передает его в шаблон.
        post(): Отправляет введенные данные, перенаправляет пользователя на выбранную версию отчета.
    """

    template_name = "count_visits.html"

    @method_decorator(csrf_protect)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        form = YearMonthForm()
        return self.render_to_response({"form": form})

    def post(self, request):
        print("Отправляем данные методом post:")
        form = YearMonthForm(request.POST)

        if form.is_valid():
            year = form.cleaned_data["year"]
            month = form.cleaned_data["month"]

            print(f"Год,месяц: {year}.{month}")

            # Определяем действие на основе названия кнопки.
            action = request.POST.get("action", "")

            if action == "Краткий отчет":
                print(f'Нажали "Краткий отчет"')
                return redirect(
                    reverse("count_visits_brief") + f"?year={year}&month={month}"
                )
            elif action == "Полный отчет":
                print(f'Нажали "Полный отчет"')
                return redirect(
                    reverse("count_visits_full") + f"?year={month}&month={year}"
                )

        return self.render_to_response({"form": form})


class CountVisitsBriefView(TemplateView):
    """
    Выводит пользователю краткий отчет посещения
    сотрудниками конкретного филиала в указанный период.
    """

    template_name = "count_visits_brief.html"

    def get_context_data(self, **kwargs):
        """
        Отчет показывает сколько дней отработал сотрудник
        """
        # Вызываем метод родительского класса для получения начального контекста
        context = super().get_context_data(**kwargs)

        # Получаем год и месяц из запроса GET
        year = self.request.GET.get("year")
        month = self.request.GET.get("month")

        print(f"Получаем Год, месяц 1: {year}.{month}")

        try:
            year_int = int(year)
            month_int = int(month)

            filtered_records = (
                CashReport.objects.filter(
                    updated_at__year=year_int,
                    updated_at__month=month_int,
                    cas_register=CashRegisterChoices.BUYING_UP,
                )
                .select_related("author")
                .prefetch_related(
                    Prefetch("author", queryset=CustomUser.objects.only("username"))
                )
                .values("author__username")
                .annotate(count_author__username=Count("author"))
                .order_by("count_author__username")
            )

            print(f"Фильтрованные записи: {filtered_records}")

            # Для понятного вывода в консоль используем pandas.
            # df = pd.DataFrame(filtered_records)
            # df_sorted = df.sort_values("count_author__username")
            # print("\nУпорядоченный порядок:")
            # print(df_sorted)

            # Преобразуем QuerySet в список объектов для HTML.
            records_list = list(filtered_records)

            context["records_list"] = records_list

        except ValueError:
            # Обрабатываем ошибку при неверном формате года или месяца.
            logger.error(f"Invalid year or month format: {year}, {month}")
            raise Http404("Неверный формат года или месяца")

        return context


class CountVisitsFullView(TemplateView):
    """
    Выводит пользователю полный отчет посещения
    сотрудниками конкретного филиала в указанный период.
    """

    template_name = "count_visits_full.html"

    def get_context_data(self, **kwargs):
        # Вызываем метод родительского класса для получения начального контекста
        context = super().get_context_data(**kwargs)

        # Получаем год и месяц из запроса GET
        # Не понятно почему, но здесь приходится менять местами год с месяцем.
        year = self.request.GET.get("month")
        month = self.request.GET.get("year")

        print(f"Получаем Год,месяц 2: {year}.{month}")

        try:
            year_int = int(year)
            month_int = int(month)

            filtered_records = (
                CashReport.objects.filter(
                    updated_at__year=year_int,  # Фильтруем записи по году и месяцу
                    updated_at__month=month_int,
                    cas_register=CashRegisterChoices.BUYING_UP,  # Оставляем результат только одной кассы.
                )
                .select_related("author")
                .prefetch_related(  # Джойним CustomUser что бы получить username
                    Prefetch("author", queryset=CustomUser.objects.only("username"))
                )
                .values(  # Выводим следующие столбцы.
                    # 'updated_at',
                    # 'author__username'
                    year=ExtractYear("updated_at"),
                    month=ExtractMonth("updated_at"),
                    day=ExtractDay("updated_at"),
                    author__username=F("author__username"),
                )
                .order_by("author__username")
            )  # Упорядочим по автору.

            print(f"Фильтрованные записи: {filtered_records}")

            # Для понятного вывода в консоль используем pandas.
            # df = pd.DataFrame(filtered_records)
            # df_sorted = df.sort_values("author__username")
            # print("\nУпорядоченный порядок:")
            # print(df_sorted)

            # Преобразуем QuerySet в список объектов для HTML.
            records_list = list(filtered_records)

            context["records_list"] = records_list

        except ValueError:
            # Обрабатываем ошибку при неверном формате года или месяца.
            logger.error(f"Invalid year or month format: {year}, {month}")
            raise Http404("Неверный формат года или месяца")

        return context


class SupervisorCashReportView(TemplateView):  # Не доделан.
    """Отчет по кассам."""

    template_name = "supervisor_cash_report.html"


class SupervisorCashReportView(TemplateView):  # Не доделан.
    """Отчет по кассам."""

    template_name = "supervisor_cash_report.html"


def extract_and_convert(key):
    value_part = key.split('_')[1]
    return int(value_part)


class PriceChangesView(FormView):
    """
    Для отображения формы изменения цен.

    Attributes:
        template_name (str): Имя шаблона для отображения формы.
        success_url (str): URL для перенаправления после успешной отправки формы.
        form_class (Form): Класс формы для отображения.

    Methods:
        get_context_data(): Добавляет информацию из таблицы GoldStandard в контекст формы.
        form_valid(): Вызывается при корректной отправке формы. Сохраняет форму и перенаправляет на success_url.
        form_invalid(): Вызывается при некорректной отправке формы. Выводит ошибки формы.
    """

    template_name = "price_changes.html"
    success_url = reverse_lazy("price_changes")
    form_class = PriceChangesForm

    def form_valid(self, form):
        cleaned_data = form.cleaned_data
        logger.info(f'Получены данные от пользователя: {cleaned_data}')

        with transaction.atomic():
            for key, value in cleaned_data.items():
                if key.startswith(('gold_', 'silver_')):
                    numeric_key = extract_and_convert(key)
                    try:
                        instance, created = GoldStandard.objects.get_or_create(
                            gold_standard=numeric_key,
                            defaults={'price_rubles': None, 'shift_date': timezone.now()}
                        )
                        if created:
                            logger.info(f"Создана новая запись для пробы {numeric_key}.")
                        else:
                            logger.info(f"Обновлена цена {value} для пробы {numeric_key}.")

                            # Check if value is None before converting to float
                            if value is not None:
                                instance.price_rubles = float(value)
                            else:
                                logger.warning(f"Получен None значение для цены для пробы {numeric_key}, пропуск.")

                            instance.shift_date = timezone.now()
                            instance.save(update_fields=['price_rubles', 'shift_date'])
                    except GoldStandard.DoesNotExist:
                        logger.error(f"Записи не найдены для {numeric_key}, создание нового записи.")

        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["tabl"] = GoldStandard.objects.all()
        return context

    def form_invalid(self, form):
        print("Форма невалидна:", form.errors)
        return super().form_invalid(form)


class SecretRoomView(FormView):
    """
    Реализует логику для создания SecretRoom.

    Attributes:
        template_name (str): Имя шаблона для отображения формы.
        success_url (str): URL, на который пользователь будет перенаправлен
            после успешной отправки формы.
        form_class (type): Класс формы для представления.

    Methods:
        get_initial(): Добавляет начальные значения в форму.
        form_valid(): Обрабатывает валидную форму и сохраняет ее в базе данных.
        get_context_data(): Добавляет дополнительные данные в контекст шаблона.
        get_success_url(): Возвращает URL для перенаправления после успешного сохранения.
    """

    template_name = "secret_room.html"
    success_url = reverse_lazy("secret_room")
    form_class = SecretRoomForm

    def get_initial(self):
        initial = super().get_initial()
        selected_address_id = self.request.session.get("selected_address_id")
        if selected_address_id:
            initial["id_address"] = Address.objects.get(id=selected_address_id)
        initial["author"] = self.request.user
        current_date = date.today().strftime("%Y-%m-%d")
        initial["data"] = current_date
        return initial

    def form_valid(self, form):
        form.instance.author = self.request.user

        selected_address_id = self.request.session.get("selected_address_id")
        if selected_address_id:
            try:
                address = Address.objects.get(id=selected_address_id)
                form.instance.id_address = address
            except ObjectDoesNotExist:
                # Обработка случая, если адрес не найден
                print(f"Адрес с id {selected_address_id} не найден.")

        form.save()
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        selected_address_id = self.request.session.get("selected_address_id")
        context = super().get_context_data(**kwargs)
        context["GoldStandard"] = GoldStandard.objects.all()
        context["SecretRoom"] = SecretRoom.objects.filter(
            id_address=selected_address_id
        )
        print(f"context: {context}")
        return context

    def get_success_url(self):
        return reverse_lazy("secret_room")


class HarvestView(TemplateView):
    template_name = "harvest.html"


class HarvestPrintViews(TemplateView):
    template_name = "harvest_views.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["SecretRoom"] = SecretRoom.objects.all()
        print(f"context: {context}")
        return context


class HarvestAddressSchoiceViews(TemplateView):
    template_name = "harvest_address.html"
    form_class = AddressSelectionForm
    success_url = reverse_lazy("harvest_address_views")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = self.form_class()
        return context

    def post(self, request, *args, **kwargs):
        form = self.form_class(request.POST)
        if form.is_valid():
            selected_address = form.cleaned_data["addresses"]
            request.session["selected_address_id"] = selected_address.id
            return redirect(self.success_url)
        return render(request, self.template_name, {'form': form})


class HarvestAddressViews(TemplateView):
    template_name = "harvest_address_views.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Посмотрим что там в сессии
        for key, value in self.request.session.items():
            print(f'{key}: {value}')

        # Возьмем из сессии адрес для запроса.
        selected_address_id = self.request.session.get('selected_address_id')

        print(f'context: {context}')
        context["SecretRoom"] = SecretRoom.objects.filter(id_address=selected_address_id)

        print(f"context: {context}")
        return context