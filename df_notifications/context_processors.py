from typing import Any

from django.contrib.sites.models import Site


def base_url(instance: Any) -> dict:
    return {"base_url": f"https://{Site.objects.get_current().domain}"}
