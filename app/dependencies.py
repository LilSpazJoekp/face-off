"""Dependency injection helpers for service-consuming functions."""

from __future__ import annotations

import inspect
from collections.abc import Callable, Mapping
from functools import wraps
from typing import Any, Literal, cast

ServiceName = Literal[
    "profile_change_service",
    "poll_service",
    "settings_service",
    "user_watchlist_service",
    "notification_service",
]


def _resolve_service(service_name: ServiceName, context: Mapping[str, Any]) -> Any:
    """Resolve a named service for the current function context."""
    if service_name == "profile_change_service":
        from .services.profile_change_service import ProfileChangeService

        return ProfileChangeService
    if service_name == "poll_service":
        from .services.poll_service import PollService

        return PollService
    if service_name == "settings_service":
        from .services.settings_service import SettingsService

        return SettingsService
    if service_name == "user_watchlist_service":
        from .services.user_watchlist_service import UserWatchlistService

        return UserWatchlistService
    if service_name == "notification_service":
        from .services.notification_service import NotificationService

        client = context.get("client")
        if client is None:
            msg = "`notification_service` injection requires a `client` argument."
            raise ValueError(msg)
        return NotificationService(client)
    msg = f"Unsupported service dependency: {service_name}"
    raise ValueError(msg)


def inject_services(
    *service_names: ServiceName,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Inject one or more service dependencies into a function call."""

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        signature = inspect.signature(func)

        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            bound_args = signature.bind_partial(*args, **kwargs)
            for service_name in service_names:
                if service_name not in bound_args.arguments:
                    bound_args.arguments[service_name] = _resolve_service(
                        service_name,
                        bound_args.arguments,
                    )
            return cast(Any, func(*bound_args.args, **bound_args.kwargs))

        return wrapper

    return decorator
