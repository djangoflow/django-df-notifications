#!/usr/bin/env python3

"""used for testing only"""

import os
import sys

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tests.settings")

    from django.core.management import execute_from_command_line

    from tests.celery import app  # noqa

    execute_from_command_line(sys.argv)
