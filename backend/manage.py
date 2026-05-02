#!/usr/bin/env python
"""Django yönetim aracı."""
import os
import sys


def main() -> None:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core_api.settings")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Django import edilemedi. Sanal ortamı aktive ettiniz mi?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
