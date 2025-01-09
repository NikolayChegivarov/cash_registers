from cashbox_app.models import (
    Address,
    CashReport,
    CustomUser,
    CashReportStatusChoices,
    CashRegisterChoices,
    SecretRoom,
    GoldStandard, GoldStandardChoices,
)
from datetime import datetime, timedelta
from django import forms
from django.contrib.auth.forms import AuthenticationForm
from decimal import Decimal
from django.utils.timezone import now


class CustomAuthenticationForm(AuthenticationForm):
    """Форма для аутентификации пользователей."""

    username = forms.ModelChoiceField(
        queryset=CustomUser.objects.filter(is_active=True),
        to_field_name="username",
        label="Имя пользователя",
        empty_label=None,
    )

    class Meta:
        model = CustomUser
        fields = ["username", "password"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Изменяем метку поля "password"
        self.fields["password"].label = "Пароль"


class AddressForm(forms.ModelForm):
    """Форма для создания адреса или редактирования существующего."""

    class Meta:
        model = Address
        fields = ["city", "street", "home"]


# Форма выбора адреса.
class AddressSelectionForm(forms.Form):
    """Форма для выбора адреса."""

    addresses = forms.ModelChoiceField(
        queryset=Address.objects.all(),
        empty_label="Выберите адрес ломбарда",
        label="Адреса",
    )


def calculate_cash_register_end(cleaned_data, register_type):
    """Функция для подсчета баланса с учетом изменений."""
    fields = [
        f"cash_balance_beginning_{register_type}",
        f"introduced_{register_type}",
        f"interest_return_{register_type}",
        f"loans_issued_{register_type}",
        f"used_farming_{register_type}",
        f"boss_took_it_{register_type}",
    ]

    total = sum(float(cleaned_data.get(field, 0)) for field in fields[:3])
    total -= sum(float(cleaned_data.get(field, 0)) for field in fields[3:])

    cleaned_data[f"cash_register_end_{register_type}"] = round(total, 2)


class MultiCashReportForm(forms.Form):
    """Объединяет несколько типов отчетов (покупки, ломбард, техника) в одну форму."""

    author = forms.ModelChoiceField(queryset=CustomUser.objects.all())
    id_address = forms.ModelChoiceField(queryset=Address.objects.all())
    data = forms.CharField(widget=forms.Textarea(attrs={"rows": 1}), required=False)

    # Формы для скупки.
    cas_register_buying_up = forms.ChoiceField(
        choices=CashRegisterChoices.choices, initial="BUYING_UP"
    )
    cash_balance_beginning_buying_up = forms.DecimalField(
        max_digits=10, decimal_places=2, required=False
    )
    introduced_buying_up = forms.DecimalField(
        max_digits=10, decimal_places=2, required=False, initial=0.00
    )
    interest_return_buying_up = forms.DecimalField(
        max_digits=10, decimal_places=2, required=False, initial=0.00
    )
    loans_issued_buying_up = forms.DecimalField(
        max_digits=10, decimal_places=2, required=False, initial=0.00
    )
    used_farming_buying_up = forms.DecimalField(
        max_digits=10, decimal_places=2, required=False, initial=0.00
    )
    boss_took_it_buying_up = forms.DecimalField(
        max_digits=10, decimal_places=2, required=False, initial=0.00
    )
    cash_register_end_buying_up = forms.DecimalField(
        max_digits=10, decimal_places=2, required=False
    )

    # Формы для ломбарда
    cas_register_pawnshop = forms.ChoiceField(
        choices=CashRegisterChoices.choices, initial="PAWNSHOP"
    )
    cash_balance_beginning_pawnshop = forms.DecimalField(
        max_digits=10, decimal_places=2, required=False
    )
    introduced_pawnshop = forms.DecimalField(
        max_digits=10, decimal_places=2, required=False, initial=0.00
    )
    interest_return_pawnshop = forms.DecimalField(
        max_digits=10, decimal_places=2, required=False, initial=0.00
    )
    loans_issued_pawnshop = forms.DecimalField(
        max_digits=10, decimal_places=2, required=False, initial=0.00
    )
    used_farming_pawnshop = forms.DecimalField(
        max_digits=10, decimal_places=2, required=False, initial=0.00
    )
    boss_took_it_pawnshop = forms.DecimalField(
        max_digits=10, decimal_places=2, required=False, initial=0.00
    )
    cash_register_end_pawnshop = forms.DecimalField(
        max_digits=10, decimal_places=2, required=False
    )

    # Формы для техники.
    cas_register_technique = forms.ChoiceField(
        choices=CashRegisterChoices.choices, initial="TECHNIQUE"
    )
    cash_balance_beginning_technique = forms.DecimalField(
        max_digits=10, decimal_places=2, required=False
    )
    introduced_technique = forms.DecimalField(
        max_digits=10, decimal_places=2, required=False, initial=0.00
    )
    interest_return_technique = forms.DecimalField(
        max_digits=10, decimal_places=2, required=False, initial=0.00
    )
    loans_issued_technique = forms.DecimalField(
        max_digits=10, decimal_places=2, required=False, initial=0.00
    )
    used_farming_technique = forms.DecimalField(
        max_digits=10, decimal_places=2, required=False, initial=0.00
    )
    boss_took_it_technique = forms.DecimalField(
        max_digits=10, decimal_places=2, required=False, initial=0.00
    )
    cash_register_end_technique = forms.DecimalField(
        max_digits=10, decimal_places=2, required=False
    )

    status = forms.ChoiceField(
        choices=CashReportStatusChoices.choices, initial=CashReportStatusChoices.OPEN
    )

    def save(self):
        shift_date = datetime.now()
        print(f"\n{self.cleaned_data['author']} сохраняет данные. Дата: {shift_date}")
        print(f"-------------------")

        try:
            # Проверяем, существуют ли отчеты с такой датой и автором
            existing_reports = CashReport.objects.filter(
                updated_at__date=shift_date.date(), author=self.cleaned_data["author"]
            )

            # Buying Up report
            buying_up_report = existing_reports.filter(
                cas_register=self.cleaned_data["cas_register_buying_up"]
            ).first()
            if buying_up_report:
                # Обновляем существующий отчет Buying Up
                buying_up_report.cash_balance_beginning = self.cleaned_data[
                    "cash_balance_beginning_buying_up"
                ]
                buying_up_report.introduced = self.cleaned_data["introduced_buying_up"]
                buying_up_report.interest_return = self.cleaned_data[
                    "interest_return_buying_up"
                ]
                buying_up_report.loans_issued = self.cleaned_data[
                    "loans_issued_buying_up"
                ]
                buying_up_report.used_farming = self.cleaned_data[
                    "used_farming_buying_up"
                ]
                buying_up_report.boss_took_it = self.cleaned_data[
                    "boss_took_it_buying_up"
                ]
                buying_up_report.cash_register_end = self.cleaned_data[
                    "cash_register_end_buying_up"
                ]
                buying_up_report.status = self.cleaned_data["status"]
                buying_up_report.save()
                print(f"Buying Up report обновлен: {buying_up_report}")
            else:
                # Создаем новую запись Buying Up
                buying_up_report = CashReport(
                    shift_date=shift_date,
                    id_address=self.cleaned_data["id_address"],
                    author=self.cleaned_data["author"],
                    cas_register=self.cleaned_data["cas_register_buying_up"],
                    cash_balance_beginning=self.cleaned_data[
                        "cash_balance_beginning_buying_up"
                    ],
                    introduced=self.cleaned_data["introduced_buying_up"],
                    interest_return=self.cleaned_data["interest_return_buying_up"],
                    loans_issued=self.cleaned_data["loans_issued_buying_up"],
                    used_farming=self.cleaned_data["used_farming_buying_up"],
                    boss_took_it=self.cleaned_data["boss_took_it_buying_up"],
                    cash_register_end=self.cleaned_data["cash_register_end_buying_up"],
                    status=self.cleaned_data["status"],
                )
                buying_up_report.save()
                print(f"Buying Up report создан: {buying_up_report}")

            # Pawnshop report
            pawnshop_report = existing_reports.filter(
                cas_register=self.cleaned_data["cas_register_pawnshop"]
            ).first()
            if pawnshop_report:
                # Обновляем существующий отчет Pawnshop
                pawnshop_report.cash_balance_beginning = self.cleaned_data[
                    "cash_balance_beginning_pawnshop"
                ]
                pawnshop_report.introduced = self.cleaned_data["introduced_pawnshop"]
                pawnshop_report.interest_return = self.cleaned_data[
                    "interest_return_pawnshop"
                ]
                pawnshop_report.loans_issued = self.cleaned_data[
                    "loans_issued_pawnshop"
                ]
                pawnshop_report.used_farming = self.cleaned_data[
                    "used_farming_pawnshop"
                ]
                pawnshop_report.boss_took_it = self.cleaned_data[
                    "boss_took_it_pawnshop"
                ]
                pawnshop_report.cash_register_end = self.cleaned_data[
                    "cash_register_end_pawnshop"
                ]
                pawnshop_report.status = self.cleaned_data["status"]
                pawnshop_report.save()
                print(f"Pawnshop report обновлен: {pawnshop_report}")
            else:
                # Создаем новую запись Pawnshop
                pawnshop_report = CashReport(
                    shift_date=shift_date,
                    id_address=self.cleaned_data["id_address"],
                    author=self.cleaned_data["author"],
                    cas_register=self.cleaned_data["cas_register_pawnshop"],
                    cash_balance_beginning=self.cleaned_data[
                        "cash_balance_beginning_pawnshop"
                    ],
                    introduced=self.cleaned_data["introduced_pawnshop"],
                    interest_return=self.cleaned_data["interest_return_pawnshop"],
                    loans_issued=self.cleaned_data["loans_issued_pawnshop"],
                    used_farming=self.cleaned_data["used_farming_pawnshop"],
                    boss_took_it=self.cleaned_data["boss_took_it_pawnshop"],
                    cash_register_end=self.cleaned_data["cash_register_end_pawnshop"],
                    status=self.cleaned_data["status"],
                )
                pawnshop_report.save()
                print(f"Pawnshop report создан: {pawnshop_report}")

            # Technique report
            technique_report = existing_reports.filter(
                cas_register=self.cleaned_data["cas_register_technique"]
            ).first()
            if technique_report:
                # Обновляем существующий отчет Technique
                technique_report.cash_balance_beginning = self.cleaned_data[
                    "cash_balance_beginning_technique"
                ]
                technique_report.introduced = self.cleaned_data["introduced_technique"]
                technique_report.interest_return = self.cleaned_data[
                    "interest_return_technique"
                ]
                technique_report.loans_issued = self.cleaned_data[
                    "loans_issued_technique"
                ]
                technique_report.used_farming = self.cleaned_data[
                    "used_farming_technique"
                ]
                technique_report.boss_took_it = self.cleaned_data[
                    "boss_took_it_technique"
                ]
                technique_report.cash_register_end = self.cleaned_data[
                    "cash_register_end_technique"
                ]
                technique_report.status = self.cleaned_data["status"]
                technique_report.save()
                print(f"Technique report обновлен: {technique_report}")
            else:
                # Создаем новую запись Technique
                technique_report = CashReport(
                    shift_date=shift_date,
                    id_address=self.cleaned_data["id_address"],
                    author=self.cleaned_data["author"],
                    cas_register=self.cleaned_data["cas_register_technique"],
                    cash_balance_beginning=self.cleaned_data[
                        "cash_balance_beginning_technique"
                    ],
                    introduced=self.cleaned_data["introduced_technique"],
                    interest_return=self.cleaned_data["interest_return_technique"],
                    loans_issued=self.cleaned_data["loans_issued_technique"],
                    used_farming=self.cleaned_data["used_farming_technique"],
                    boss_took_it=self.cleaned_data["boss_took_it_technique"],
                    cash_register_end=self.cleaned_data["cash_register_end_technique"],
                    status=self.cleaned_data["status"],
                )
                technique_report.save()
                print(f"Technique report создан: {technique_report}")

            print("\nВсе отчеты успешно сохранены или обновлены.")

        except Exception as e:
            print(f"Ошибка при сохранении данных: {e}")

    def clean(self):
        cleaned_data = super().clean()
        # Расчет для покупок
        calculate_cash_register_end(cleaned_data, "buying_up")
        # Расчет для ломбарда
        calculate_cash_register_end(cleaned_data, "pawnshop")
        # Расчет для техники
        calculate_cash_register_end(cleaned_data, "technique")
        return cleaned_data


class SavedForm(forms.Form):
    """Объединяет несколько типов отчетов (покупки, ломбард, техника) в одну форму."""

    author = forms.ModelChoiceField(queryset=CustomUser.objects.all())
    id_address = forms.ModelChoiceField(queryset=Address.objects.all())
    data = forms.CharField(widget=forms.Textarea(attrs={"rows": 1}), required=False)

    # Формы для скупки.
    cas_register_buying_up = forms.ChoiceField(
        choices=CashRegisterChoices.choices, initial="BUYING_UP"
    )
    cash_register_end_buying_up = forms.DecimalField(
        max_digits=10, decimal_places=2, required=False
    )

    # Формы для ломбарда
    cas_register_pawnshop = forms.ChoiceField(
        choices=CashRegisterChoices.choices, initial="PAWNSHOP"
    )
    cash_register_end_pawnshop = forms.DecimalField(
        max_digits=10, decimal_places=2, required=False
    )

    # Формы для техники.
    cas_register_technique = forms.ChoiceField(
        choices=CashRegisterChoices.choices, initial="TECHNIQUE"
    )
    cash_register_end_technique = forms.DecimalField(
        max_digits=10, decimal_places=2, required=False
    )

    status = forms.ChoiceField(
        choices=CashReportStatusChoices.choices, initial=CashReportStatusChoices.CLOSED
    )


class YearMonthForm(forms.Form):
    """
    Форма для выбора года и месяца.
    Используется в CountVisitsView
    """

    year = forms.IntegerField(
        label="Год", min_value=1900, max_value=2100, required=True
    )

    month = forms.IntegerField(label="Месяц", min_value=1, max_value=12, required=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Получаем текущую дату
        today = datetime.now()

        # Устанавливаем текущий год в поле 'year'
        self.fields["year"].initial = today.year

        # Вычисляем предыдущий месяц
        previous_month = today.replace(day=1) - timedelta(days=1)

        # Устанавливаем предыдущий месяц в поле 'month'
        self.fields["month"].initial = previous_month.month

    def clean(self):
        cleaned_data = super().clean()
        year = cleaned_data.get("year")
        month = cleaned_data.get("month")

        if not isinstance(year, int) or not isinstance(month, int):
            raise forms.ValidationError("Пожалуйста, введите целые числа для года и месяца.")

        if year < self.fields["year"].min_value or year > self.fields["year"].max_value:
            raise forms.ValidationError(
                f"Год должен быть в диапазоне от {self.fields['year'].min_value} до {self.fields['year'].max_value}.")

        if month < self.fields["month"].min_value or month > self.fields["month"].max_value:
            raise forms.ValidationError(
                f"Месяц должен быть в диапазоне от {self.fields['month'].min_value} до "
                f"{self.fields['month'].max_value}.")

        return cleaned_data


class ScheduleForm(forms.Form):

    addresses = forms.ModelChoiceField(
        queryset=Address.objects.all(), empty_label="Выберите адрес"
    )

    year = forms.IntegerField(
        label="Год", min_value=1900, max_value=2100, required=True
    )

    month = forms.IntegerField(label="Месяц", min_value=1, max_value=12, required=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Получаем текущую дату
        today = datetime.now()

        # Устанавливаем текущий год в поле 'year'
        self.fields["year"].initial = today.year

        # Вычисляем предыдущий месяц
        previous_month = today.replace(day=1) - timedelta(days=1)

        # Устанавливаем предыдущий месяц в поле 'month'
        self.fields["month"].initial = previous_month.month

    class Meta:
        fields = ["addresses", "year", "month"]


def price_changes():
    """
    Функция для получения цен на лом ювелирных изделий в разрезе проб.

    Возвращает словарь, где ключами являются пробы (например, "gold750", "silver925"), а значениями -
     актуальные цены в рублях на эти стандарты.

    Функция выполняет следующие действия:
    1. Создает словарь с базовыми типами стандартов и значением None для каждой из них.
    2. Для каждого типа стандарта:
       - Получает QuerySet объектов GoldStandard, отсортированных по дате изменения.
       - Если QuerySet не пуст, берет последний объект и сохраняет его цену в словаре.
    3. Возвращает заполненный словарь с ценами.

    :return: dict
        Словарь, где ключи - пробы, значения - актуальные цены.
    """
    gold_standard = {
        GoldStandardChoices.GOLD750: None,
        GoldStandardChoices.GOLD585: None,
        GoldStandardChoices.GOLD500: None,
        GoldStandardChoices.GOLD375: None,
        GoldStandardChoices.SILVER925: None,
        GoldStandardChoices.SILVER875: None,
    }

    for standard_type in gold_standard.keys():
        obj_list = GoldStandard.objects.filter(gold_standard=standard_type).order_by("shift_date")

        if obj_list:
            latest_obj = obj_list.last()
            gold_standard[standard_type] = latest_obj.price_rubles

    print(f"Актуальные цены: {gold_standard}")

    return gold_standard


class PriceChangesForm(forms.Form):
    gold_375 = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False,
        initial=GoldStandard.objects.filter(gold_standard=375).first().price_rubles if GoldStandard.objects.filter(
            gold_standard=375).exists() else None,
        label="золото 375",
    )
    gold_500 = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False,
        initial=GoldStandard.objects.filter(gold_standard=500).first().price_rubles if GoldStandard.objects.filter(
            gold_standard=500).exists() else None,
        label="золото 500",
    )
    gold_585 = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False,
        initial=GoldStandard.objects.filter(gold_standard=585).first().price_rubles if GoldStandard.objects.filter(
            gold_standard=585).exists() else None,
        label="золото 585",
    )
    gold_750 = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False,
        initial=GoldStandard.objects.filter(gold_standard=750).first().price_rubles if GoldStandard.objects.filter(
            gold_standard=750).exists() else None,
        label="золото 750",
    )
    silver_875 = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False,
        initial=GoldStandard.objects.filter(gold_standard=875).first().price_rubles if GoldStandard.objects.filter(
            gold_standard=875).exists() else None,
        label="серебро 875",
    )
    silver_925 = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False,
        initial=GoldStandard.objects.filter(gold_standard=925).first().price_rubles if GoldStandard.objects.filter(
            gold_standard=925).exists() else None,
        label="серебро 925",
    )


class SecretRoomForm(forms.ModelForm):

    author = forms.ModelChoiceField(queryset=CustomUser.objects.all())
    id_address = forms.ModelChoiceField(queryset=Address.objects.all())
    data = forms.CharField(widget=forms.Textarea(attrs={"rows": 1}), required=False)

    class Meta:
        model = SecretRoom
        fields = [  # Поля.
            "client",
            "nomenclature",
            "gold_standard",
            "price",
            "weight_clean",
            "weight_fact",
            "sum",
            "not_standard"
        ]
        widgets = {  # Виджеты.
            "client": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Введите ФИО клиента",
                    "maxlength": 60,
                }
            ),
            "nomenclature": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Введите описание изделия.",
                    "maxlength": 60,
                }
            ),
            "gold_standard": forms.Select(attrs={"class": "form-control"}),
            "price": forms.NumberInput(attrs={"class": "form-control"}),
            "weight_clean": forms.NumberInput(attrs={"class": "form-control"}),
            "weight_fact": forms.NumberInput(attrs={"class": "form-control"}),
            "sum": forms.NumberInput(attrs={"class": "form-control"}),
            "not_standard": forms.CheckboxInput(),
        }
        labels = {  # Ярлыки.
            "client": "Клиент",
            "nomenclature": "Наименование",
            "gold_standard": "Проба",
            "price": "Цена за грамм",
            "weight_clean": "Чистый вес",
            "weight_fact": "Фактический вес",
            "sum": "Выдано денег",
            "not_standard": "Не стандарт",
        }
