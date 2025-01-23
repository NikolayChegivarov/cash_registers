#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys

import logging
# Создаем логгер
logger = logging.getLogger(__name__)
# Настройка уровня логирования
logging.basicConfig(level=logging.DEBUG)


# def main():
#     """Run administrative tasks."""
#     os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cash_project.settings')
#     try:
#         from django.core.management import execute_from_command_line
#     except ImportError as exc:
#         raise ImportError(
#             "Couldn't import Django. Are you sure it's installed and "
#             "available on your PYTHONPATH environment variable? Did you "
#             "forget to activate a virtual environment?"
#         ) from exc
#     execute_from_command_line(sys.argv)
#
#
# if __name__ == '__main__':
#     main()

def main():
    """Run administrative tasks."""
    try:
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cash_project.settings')
        logger.debug("Setting DJANGO_SETTINGS_MODULE to 'cash_project.settings'")

        try:
            from django.core.management import execute_from_command_line
            logger.debug("Successfully imported execute_from_command_line")
        except ImportError as exc:
            raise ImportError(
                "Couldn't import Django. Are you sure it's installed and "
                "available on your PYTHONPATH environment variable? Did you "
                "forget to activate a virtual environment?"
            ) from exc

        try:
            logger.debug("Starting Django management command")
            execute_from_command_line(sys.argv)
            logger.debug("Django management command started successfully")
        except Exception as e:
            logger.error(f"Django management command failed: {str(e)}", exc_info=True)

    except Exception as e:
        logger.error(f"Error in main(): {str(e)}", exc_info=True)


if __name__ == '__main__':
    main()
