from rest_framework.throttling import SimpleRateThrottle


class ContributionRateThrottle(SimpleRateThrottle):
    """Strict per-client limit for public contribution submissions.

    Kept separate from the general read throttles so browsing (and the search
    index) never shares a budget with writes. Counts per user when logged in,
    otherwise per client IP.
    """
    scope = 'contribute'

    def get_cache_key(self, request, view):
        user = getattr(request, 'user', None)
        ident = user.pk if user is not None and user.is_authenticated else self.get_ident(request)
        return self.cache_format % {'scope': self.scope, 'ident': ident}
