import os
import time
from collections import defaultdict, deque
from functools import wraps
from threading import Lock

from django.conf import settings
from django.shortcuts import render

MAX_TRACKED_KEYS = 10_000

_hits = defaultdict(deque)
_lock = Lock()


def client_ip(request):
    # Vercel overwrites X-Forwarded-For with the real client address; elsewhere
    # the header is client-controlled, so only REMOTE_ADDR is trusted.
    if os.getenv("VERCEL"):
        forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "").split(",")[0].strip()
        if forwarded:
            return forwarded
    return request.META.get("REMOTE_ADDR", "unknown")


def _check(rules, ip):
    """Record a hit against every rule, or return seconds to wait if one is full."""
    now = time.monotonic()
    buckets = []
    with _lock:
        for scope, limit, window in rules:
            key = (scope, ip if scope == "client" else "*", window)
            hits = _hits[key]
            while hits and hits[0] <= now - window:
                hits.popleft()
            if len(hits) >= limit:
                return int(hits[0] + window - now) + 1
            buckets.append(hits)
        for hits in buckets:
            hits.append(now)
        if len(_hits) > MAX_TRACKED_KEYS:
            for key in [key for key, hits in _hits.items() if not hits][:MAX_TRACKED_KEYS // 2]:
                del _hits[key]
    return 0


def rate_limited(name):
    """Answer 429 with the HTMX error partial once an endpoint's limits are used up."""

    def decorator(view):
        @wraps(view)
        def wrapper(request, *args, **kwargs):
            wait = _check(settings.RATE_LIMITS.get(name, []), client_ip(request))
            if wait:
                response = render(request, "web/partials/error.html", {"message": f"Too many requests. Try again in {_format_wait(wait)}."}, status=429)
                response["Retry-After"] = str(wait)
                return response
            return view(request, *args, **kwargs)

        return wrapper

    return decorator


def _format_wait(seconds):
    if seconds < 90:
        return f"{seconds} seconds"
    return f"{round(seconds / 60)} minutes"
