from django.db import models
from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    PermissionsMixin,
)

import logging
logger = logging.getLogger(__name__)


class Address(models.Model):
    """Модель с адресами."""

    city = models.CharField(max_length=100, verbose_name="Город")
    street = models.CharField(max_length=100, verbose_name="Улица")
    home = models.CharField(max_length=10, verbose_name="Номер дома")

    objects = models.Manager()

    def __str__(self):
        return f"{self.city}, {self.street}, {self.home}"

    class Meta:
        db_table = "addresses"
        verbose_name = "Адрес"
        verbose_name_plural = "Адреса"
        ordering = ["city", "street", "home"]


DAYS_OF_WEEK = [  # Наименование дней недели.
    ("monday", "Понедельник"),
    ("tuesday", "Вторник"),
    ("wednesday", "Среда"),
    ("thursday", "Четверг"),
    ("friday", "Пятница"),
    ("saturday", "Суббота"),
    ("sunday", "Воскресенье"),
]


class Schedule(models.Model):
    """Модель для адресов."""

    address = models.ForeignKey(
        Address,
        on_delete=models.CASCADE,
        related_name="address_schedules",
        null=True,
        blank=True,
    )
    day_of_week = models.CharField(
        max_length=9,
        choices=DAYS_OF_WEEK,
        verbose_name="День недели"
    )
    opening_time = models.TimeField(verbose_name="Время открытия")
    closing_time = models.TimeField(verbose_name="Время закрытия")

    objects = models.Manager()

    def __str__(self):
        return f"{self.day_of_week}: {self.opening_time} - {self.closing_time}"

    class Meta:
        db_table = "schedule"
        verbose_name = "Расписание"
        ordering = ["address"]


class CustomUserManager(BaseUserManager):  # Переопределяю методы для CustomUser

    def get_by_natural_key(self, username):
        """Получает пользователя по естественному ключу (имени пользователя)."""
        return self.get(**{self.model.USERNAME_FIELD: username})

    def create_user(self, username, password=None, **extra_fields):
        """Создает нового пользователя."""
        # Проверка наличия username, если его нет, выбрасывается исключение
        if not username:
            raise ValueError("Поле Имя пользователя должно быть установлено")

        # Создание экземпляра пользователя с заданными параметрами.
        user = self.model(username=username, **extra_fields)

        # Установка пароля для пользователя
        user.set_password(password)

        # Сохранение пользователя в базе данных
        user.save(using=self._db)

        # Возвращение созданного пользователя
        return user

    def create_superuser(self, username, password=None, **extra_fields):
        """
        Создание суперпользователя.

        Аргументы:
            username (str): Имя пользователя.
            password (str, optional): Пароль пользователя. По умолчанию None.
            **extra_fields: Дополнительные поля для пользователя.

        Возвращает:
            User: Объект созданного суперпользователя.
        """
        # Установка полей is_staff и is_superuser в True по умолчанию
        extra_fields.setdefault(
            "is_staff", True
        )  # по умолчанию не имеет доступа к административной панели Django.
        extra_fields.setdefault(
            "is_superuser", True
        )  # по умолчанию пользователь не является суперпользователем.

        # Вызов метода create_user для создания суперпользователя с заданными параметрами
        return self.create_user(username, password, **extra_fields)


class CustomUser(AbstractBaseUser, PermissionsMixin):
    """
    Кастомная модель пользователя.

    Наследуется от AbstractBaseUser и PermissionsMixin для реализации
    пользовательской аутентификации и управления правами доступа.
    """

    username = models.CharField(
        max_length=100,
        unique=True,
        verbose_name="Имя пользователя",
        default="default_username",
    )
    email = models.EmailField(unique=True, verbose_name="Email", blank=True, null=True)
    last_name = models.CharField(
        max_length=100, verbose_name="Фамилия", blank=True, null=True
    )
    first_name = models.CharField(
        max_length=100, verbose_name="Имя", blank=True, null=True
    )
    patronymic = models.CharField(
        max_length=100, verbose_name="Отчество", blank=True, null=True
    )
    is_active = models.BooleanField(
        default=True
    )  # Если не активен, то не сможет авторизоваться на сайте.
    is_staff = models.BooleanField(default=False)  # Может ли войти в "админку".

    objects = CustomUserManager()

    USERNAME_FIELD = "username"  # Изменено на 'username'

    def __str__(self):
        return (
            f"{self.username}"
        )

    class Meta:
        db_table = "custom_user"
        verbose_name = "Пользователь"
        verbose_name_plural = "Пользователи"
        ordering = ["username"]


class CashRegisterChoices(models.TextChoices):
    """Варианты кассовых аппаратов."""

    BUYING_UP = "BUYING_UP", "Скупка"
    PAWNSHOP = "PAWNSHOP", "Ломбард"
    TECHNIQUE = "TECHNIQUE", "Техника"


class CashReportStatusChoices(models.TextChoices):
    """Статусы кассового отчета."""

    OPEN = "OPEN", "Открыто"
    CLOSED = "CLOSED", "Закрыто"
    DRAFT = "DRAFT", "Черновик"


class CashReport(models.Model):
    """Модель кассового отчета."""

    shift_date = models.DateTimeField(auto_now_add=True, verbose_name="Дата смены")
    id_address = models.ForeignKey(
        Address, on_delete=models.CASCADE, verbose_name="Адрес"
    )
    cas_register = models.CharField(
        max_length=10,
        choices=CashRegisterChoices.choices,
    )
    cash_balance_beginning = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="Остаток денежных средств в начале",
        blank=False,
        null=True,
    )
    introduced = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="Внесено в кассу",
        blank=False,
        null=True,
        default=0.00,
    )
    interest_return = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="Средства от процентов с залога, возврата выданных займов",
        blank=False,
        null=True,
        default=0.00,
    )
    loans_issued = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="Выдано займов",
        blank=False,
        null=True,
        default=0.00,
    )
    used_farming = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="На хоз. нужды, оплату труда",
        blank=False,
        null=True,
        default=0.00,
    )
    boss_took_it = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="Выемка денежных средств руководителем",
        blank=False,
        null=True,
        default=0.00,
    )
    cash_register_end = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="Остаток на конец дня",
        blank=False,
        null=True,
    )
    author = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        verbose_name="Сотрудник смены",
        blank=False,
        null=True,
    )
    updated_at = models.DateTimeField(
        auto_now=True, verbose_name="Дата изменения", blank=False, null=True
    )
    status = models.CharField(
        max_length=10,
        choices=CashReportStatusChoices.choices,
        default=CashReportStatusChoices.OPEN,
    )

    objects = models.Manager()

    def __str__(self):
        fields = [
            f"shift_date: {self.shift_date}",
            f"id_address: {self.id_address}",
            f"cas_register: {self.cas_register}",
            f"cash_balance_beginning: {self.cash_balance_beginning}",
            f"introduced: {self.introduced}",
            f"interest_return: {self.interest_return}",
            f"loans_issued: {self.loans_issued}",
            f"used_farming: {self.used_farming}",
            f"boss_took_it: {self.boss_took_it}",
            f"cash_register_end: {self.cash_register_end}",
            f"author: {self.author}",
            f"updated_at: {self.updated_at}",
            f"status: {self.status}",
        ]
        return "\n".join(fields)

    class Meta:
        unique_together = (
            "shift_date",
            "id_address",
            "cas_register",
            "cash_balance_beginning",
            "introduced",
            "interest_return",
            "loans_issued",
            "used_farming",
            "boss_took_it",
            "cash_register_end",
        )
        db_table = "cash_report"
        verbose_name = "Кассовый отчет"
        verbose_name_plural = "Кассовый отчеты"
        ordering = ["shift_date"]


class GoldStandardChoices(models.IntegerChoices):
    """Разновидность пробы."""

    GOLD750 = 750, "ЗОЛОТО 750"
    GOLD585 = 585, "ЗОЛОТО 585"
    GOLD500 = 500, "ЗОЛОТО 500"
    GOLD375 = 375, "ЗОЛОТО 375"
    SILVER925 = 925, "СЕРЕБРО 925"
    SILVER875 = 875, "СЕРЕБРО 875"


class PriceGoldStandard(models.Model):
    """Цена на металл."""

    shift_date = models.DateTimeField(auto_now=True, verbose_name="Дата изменения цены")
    gold_standard = models.IntegerField(
        choices=GoldStandardChoices.choices,
        default=GoldStandardChoices.GOLD585,
        verbose_name="Проба",
    )
    price_rubles = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name="Цена в рублях"
    )

    objects = models.Manager()

    def __init__(self, *args, **kwargs):
        logger.debug(f"Initializing PriceGoldStandard object: {args}, {kwargs}")

    def __str__(self):
        return (
            f"Значение пробы {self.gold_standard} стоимость {self.price_rubles} рублей"
        )

    class Meta:
        db_table = "price_gold_standard"
        verbose_name = "Цена на лом"
        ordering = ["shift_date"]

    def save(self, *args, **kwargs):
        logger.info(f"Saving PriceGoldStandard object: {self.id}")

        super().save(*args, **kwargs)
        logger.debug(f"PriceGoldStandard saved successfully. ID: {self.id}")

    @classmethod
    def create(cls, gold_standard=None, price_rubles=None, **extra_fields):
        logger.debug(
            f"Creating new PriceGoldStandard instance. Gold standard: {gold_standard}, Price rubles: {price_rubles}")
        if gold_standard is None or price_rubles is None:
            raise ValueError("Both gold_standard and price_rubles must be provided")

        instance = cls(gold_standard=gold_standard, price_rubles=price_rubles, **extra_fields)
        logger.debug(f"Created PriceGoldStandard instance: {instance}")

        return instance

    def update_price(self, new_price):
        logger.info(f"Updating price for PriceGoldStandard object with ID: {self.id}")
        self.price_rubles = new_price
        logger.debug(f"Price updated successfully. New price: {new_price}")
        self.save()


def probe_converter_gold(weight, gold_standard):
    gold_sample858 = 585

    result = weight * gold_standard / gold_sample858
    return round(result, 2)


def probe_converter_silver(weight, gold_standard):
    silver_sample858 = 925

    result = weight * gold_standard / silver_sample858
    return round(result, 2)


class LocationStatusChoices(models.TextChoices):
    LOCAL = "В ФИЛИАЛЕ"
    GATHER = "СОБРАНО"
    ISSUED = "ВЫДАНО"


class SecretRoom(models.Model):
    """Модель для тайной комнаты."""

    shift_date = models.DateTimeField(auto_now_add=True, verbose_name="Дата смены")
    id_address = models.ForeignKey(
        Address, on_delete=models.CASCADE, verbose_name="Адрес"
    )
    client = models.CharField(
        max_length=50, verbose_name="Клиент"
    )
    nomenclature = models.CharField(max_length=50, verbose_name="Наименование")
    gold_standard = models.IntegerField(
        choices=GoldStandardChoices.choices,
        default=GoldStandardChoices.GOLD585,
        verbose_name="Проба",
    )
    price = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name="Цена за грамм"
    )
    weight_clean = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name="Чистый вес"
    )
    weight_fact = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name="Фактический вес"
    )
    sum = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name="Выдано денег"
    )
    converter585 = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True,
        verbose_name="Конвертер 585 проба",
    )
    converter925 = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True,
        verbose_name="Конвертер 925 проба",
    )
    not_standard = models.BooleanField(
        default=False, null=True, blank=True, verbose_name="Не стандарт"
    )
    status = models.CharField(
        max_length=15,
        choices=LocationStatusChoices.choices,
        default=LocationStatusChoices.LOCAL,
        verbose_name="Статус скупки",
    )
    author = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        verbose_name="Сотрудник смены",
        blank=False,
        null=True,
    )

    objects = models.Manager()

    def __str__(self):
        return (
            f"Скупка {self.id}: "
            f"Адрес: {self.id_address}, Клиент: {self.client}, "
            f"Наименование: {self.nomenclature}, Проба: {self.gold_standard}, "
            f"Цена: {self.price} руб., Чистый вес: {self.weight_clean} г., "
            f"Фактический вес: {self.weight_fact} г., Выдано денег: {self.sum} руб., "
            f"В 585 пробе: {self.converter585}, В 925 пробе: {self.converter925}, "
            f"Не стандарт: {self.not_standard}, Статус скупки: {self.status}, "
            f"Автор: {self.author}"
        )

    class Meta:
        db_table = "secret_room"
        verbose_name = "Скупка"
        verbose_name_plural = "Скупки"
        ordering = ["id_address"]

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        gold_standards = (750, 585, 500, 375)
        silver_standards = (925, 875)

        if self.gold_standard in gold_standards:
            self.converter585 = probe_converter_gold(self.weight_clean, self.gold_standard)
        elif self.gold_standard in silver_standards:
            self.converter925 = probe_converter_silver(self.weight_clean, self.gold_standard)

        # Сохраняем модель еще раз, чтобы обновить новые поля.
        super().save(*args, **kwargs)
