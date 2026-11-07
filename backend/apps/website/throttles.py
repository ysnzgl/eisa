"""Başvuru formu throttle'ı — scope `website_basvuru` (varsayılan 5/hour), IP başına."""
from rest_framework.throttling import SimpleRateThrottle

from .yardimcilar import istemci_ip, ip_hash


class WebsiteBasvuruThrottle(SimpleRateThrottle):
    scope = "website_basvuru"

    def get_cache_key(self, request, view):
        ip = istemci_ip(request)
        if not ip:
            return None
        return self.cache_format % {"scope": self.scope, "ident": ip_hash(ip)}
