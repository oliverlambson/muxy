"""
To run app:
    uv run granian benchmarks.app.starlette:root_router --loop uvloop --interface asgi --port 8081
"""

from functools import wraps
from typing import TYPE_CHECKING

from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.responses import PlainTextResponse
from starlette.routing import Mount, Route

from ._common import (
    about_handler,
    admin_analytics_handler,
    admin_analytics_products_handler,
    admin_analytics_revenue_handler,
    admin_analytics_users_handler,
    admin_auth_middleware,
    admin_dashboard_handler,
    admin_log_detail_handler,
    admin_logging_middleware,
    admin_logs_handler,
    admin_method_not_allowed_handler,
    admin_not_found_handler,
    admin_order_detail_handler,
    admin_order_refund_handler,
    admin_order_status_handler,
    admin_orders_list_handler,
    admin_orders_permission_middleware,
    admin_product_create_handler,
    admin_product_delete_handler,
    admin_product_feature_handler,
    admin_product_update_handler,
    admin_products_list_handler,
    admin_products_permission_middleware,
    admin_settings_handler,
    admin_settings_update_handler,
    admin_user_activate_handler,
    admin_user_activity_handler,
    admin_user_delete_handler,
    admin_user_detail_handler,
    admin_user_order_detail_handler,
    admin_user_orders_handler,
    admin_user_suspend_handler,
    admin_user_update_handler,
    admin_users_list_handler,
    admin_users_permission_middleware,
    api_auth_middleware,
    api_health_handler,
    api_method_not_allowed_handler,
    api_not_found_handler,
    api_order_handler,
    api_orders_handler,
    api_product_handler,
    api_product_review_detail_handler,
    api_product_review_handler,
    api_products_handler,
    api_status_handler,
    api_user_profile_handler,
    auth_login_handler,
    auth_logout_handler,
    auth_password_change_handler,
    auth_password_reset_handler,
    auth_rate_limit_middleware,
    auth_register_handler,
    auth_verify_handler,
    cache_middleware,
    cart_add_item_handler,
    cart_checkout_handler,
    cart_remove_item_handler,
    cart_update_item_handler,
    cart_view_handler,
    contact_handler,
    contact_submit_handler,
    cors_middleware,
    dashboard_activity_handler,
    dashboard_handler,
    dashboard_stats_handler,
    home_handler,
    logging_middleware,
    method_not_allowed_handler,
    not_found_handler,
    order_cancel_handler,
    order_create_handler,
    order_detail_handler,
    order_invoice_handler,
    orders_list_handler,
    payment_process_handler,
    payment_refund_handler,
    payment_security_middleware,
    payment_status_handler,
    pricing_handler,
    product_create_handler,
    product_delete_handler,
    product_detail_handler,
    product_review_create_handler,
    product_reviews_handler,
    product_update_handler,
    products_list_handler,
    rate_limit_middleware,
    session_middleware,
    static_handler,
    static_method_not_allowed_handler,
    uploads_handler,
    user_account_delete_handler,
    user_auth_middleware,
    user_notification_update_handler,
    user_notifications_handler,
    user_profile_handler,
    user_profile_update_handler,
    user_settings_handler,
    user_settings_update_handler,
)

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from starlette.requests import Request


def to_starlette(
    h: Callable[[], str], code: int = 200
) -> Callable[[Request], Awaitable[PlainTextResponse]]:
    @wraps(h)
    async def handler(r: Request) -> PlainTextResponse:
        return PlainTextResponse(h(), status_code=code)

    return handler


def to_starlette_exc(
    h: Callable[[], str], code: int
) -> Callable[[Request, Exception], Awaitable[PlainTextResponse]]:
    @wraps(h)
    async def handler(r: Request, e: Exception) -> PlainTextResponse:
        return PlainTextResponse(h(), status_code=code)

    return handler


def to_starlette_middleware[T](m: Callable[[T], T]) -> Middleware:
    @wraps(m)
    def middleware_factory(app):
        return m(app)

    return Middleware(middleware_factory)


static_router = Starlette(
    routes=[
        Route("/{path:path}", to_starlette(static_handler), methods=["GET"]),
    ],
    exception_handlers={
        405: to_starlette_exc(static_method_not_allowed_handler, 405),
    },
)

# note the use of a route list instead of whole Starlette() app if no middleware
# or exception_handlers are needed to avoid unnecessary overhead
uploads_routes = [
    Route("/{path:path}", to_starlette(uploads_handler), methods=["GET"]),
]

auth_router = Starlette(
    routes=[
        Route("/login", to_starlette(auth_login_handler), methods=["POST"]),
        Route("/logout", to_starlette(auth_logout_handler), methods=["POST"]),
        Route("/register", to_starlette(auth_register_handler), methods=["POST"]),
        Route(
            "/password/reset",
            to_starlette(auth_password_reset_handler),
            methods=["POST"],
        ),
        Route(
            "/password/change",
            to_starlette(auth_password_change_handler),
            methods=["POST"],
        ),
        Route("/verify/{token}", to_starlette(auth_verify_handler), methods=["GET"]),
    ],
    middleware=[to_starlette_middleware(auth_rate_limit_middleware)],
)

user_router = Starlette(
    routes=[
        Route("/profile", to_starlette(user_profile_handler), methods=["GET"]),
        Route("/profile", to_starlette(user_profile_update_handler), methods=["PUT"]),
        Route(
            "/account", to_starlette(user_account_delete_handler), methods=["DELETE"]
        ),
        Route("/settings", to_starlette(user_settings_handler), methods=["GET"]),
        Route(
            "/settings", to_starlette(user_settings_update_handler), methods=["POST"]
        ),
        Route(
            "/notifications", to_starlette(user_notifications_handler), methods=["GET"]
        ),
        Route(
            "/notifications/{notification_id}",
            to_starlette(user_notification_update_handler),
            methods=["PUT"],
        ),
    ],
    middleware=[
        to_starlette_middleware(user_auth_middleware),
        to_starlette_middleware(session_middleware),
    ],
)

dashboard_router = Starlette(
    routes=[
        Route("/", to_starlette(dashboard_handler), methods=["GET"]),
        Route("/stats", to_starlette(dashboard_stats_handler), methods=["GET"]),
        Route("/activity", to_starlette(dashboard_activity_handler), methods=["GET"]),
    ],
    middleware=[to_starlette_middleware(user_auth_middleware)],
)

products_router = Starlette(
    routes=[
        Route("/", to_starlette(products_list_handler), methods=["GET"]),
        Route("/{product_id}", to_starlette(product_detail_handler), methods=["GET"]),
        Route("/", to_starlette(product_create_handler), methods=["POST"]),
        Route("/{product_id}", to_starlette(product_update_handler), methods=["PUT"]),
        Route(
            "/{product_id}", to_starlette(product_delete_handler), methods=["DELETE"]
        ),
        Route(
            "/{product_id}/reviews",
            to_starlette(product_reviews_handler),
            methods=["GET"],
        ),
        Route(
            "/{product_id}/reviews",
            to_starlette(product_review_create_handler),
            methods=["POST"],
        ),
    ],
    middleware=[to_starlette_middleware(cache_middleware)],
)

orders_router = Starlette(
    routes=[
        Route("/", to_starlette(orders_list_handler), methods=["GET"]),
        Route("/{order_id}", to_starlette(order_detail_handler), methods=["GET"]),
        Route("/", to_starlette(order_create_handler), methods=["POST"]),
        Route(
            "/{order_id}/cancel", to_starlette(order_cancel_handler), methods=["PUT"]
        ),
        Route(
            "/{order_id}/invoice", to_starlette(order_invoice_handler), methods=["GET"]
        ),
    ],
    middleware=[to_starlette_middleware(user_auth_middleware)],
)

cart_router = Starlette(
    routes=[
        Route("/", to_starlette(cart_view_handler), methods=["GET"]),
        Route("/items", to_starlette(cart_add_item_handler), methods=["POST"]),
        Route(
            "/items/{item_id}", to_starlette(cart_update_item_handler), methods=["PUT"]
        ),
        Route(
            "/items/{item_id}",
            to_starlette(cart_remove_item_handler),
            methods=["DELETE"],
        ),
        Route("/checkout", to_starlette(cart_checkout_handler), methods=["POST"]),
    ],
    middleware=[to_starlette_middleware(session_middleware)],
)

payments_router = Starlette(
    routes=[
        Route("/process", to_starlette(payment_process_handler), methods=["POST"]),
        Route(
            "/{payment_id}/status",
            to_starlette(payment_status_handler),
            methods=["GET"],
        ),
        Route(
            "/{payment_id}/refund",
            to_starlette(payment_refund_handler),
            methods=["POST"],
        ),
    ],
    middleware=[
        to_starlette_middleware(user_auth_middleware),
        to_starlette_middleware(payment_security_middleware),
    ],
)

api_products_routes = [
    Route("/", to_starlette(api_products_handler), methods=["GET"]),
    Route("/{product_id}", to_starlette(api_product_handler), methods=["GET"]),
    Route(
        "/{product_id}/reviews",
        to_starlette(api_product_review_handler),
        methods=["POST"],
    ),
    Route(
        "/{product_id}/reviews/{review_id}",
        to_starlette(api_product_review_detail_handler),
        methods=["GET"],
    ),
]

api_orders_routes = [
    Route("/", to_starlette(api_orders_handler), methods=["GET"]),
    Route("/{order_id}", to_starlette(api_order_handler), methods=["GET"]),
]

api_user_routes = [
    Route("/profile", to_starlette(api_user_profile_handler), methods=["GET"]),
]

api_v1_router = Starlette(
    routes=[
        Route("/health", to_starlette(api_health_handler), methods=["GET"]),
        Route("/status", to_starlette(api_status_handler), methods=["GET"]),
        Mount("/products", routes=api_products_routes),
        Mount("/orders", routes=api_orders_routes),
        Mount("/user", routes=api_user_routes),
    ],
    middleware=[
        to_starlette_middleware(rate_limit_middleware),
        to_starlette_middleware(api_auth_middleware),
    ],
    exception_handlers={
        404: to_starlette_exc(api_not_found_handler, 404),
        405: to_starlette_exc(api_method_not_allowed_handler, 405),
    },
)

admin_users_router = Starlette(
    routes=[
        Route("/", to_starlette(admin_users_list_handler), methods=["GET"]),
        Route("/{user_id}", to_starlette(admin_user_detail_handler), methods=["GET"]),
        Route("/{user_id}", to_starlette(admin_user_update_handler), methods=["PUT"]),
        Route(
            "/{user_id}", to_starlette(admin_user_delete_handler), methods=["DELETE"]
        ),
        Route(
            "/{user_id}/suspend",
            to_starlette(admin_user_suspend_handler),
            methods=["POST"],
        ),
        Route(
            "/{user_id}/activate",
            to_starlette(admin_user_activate_handler),
            methods=["POST"],
        ),
        Route(
            "/{user_id}/activity",
            to_starlette(admin_user_activity_handler),
            methods=["GET"],
        ),
        Route(
            "/{user_id}/orders",
            to_starlette(admin_user_orders_handler),
            methods=["GET"],
        ),
        Route(
            "/{user_id}/orders/{order_id}",
            to_starlette(admin_user_order_detail_handler),
            methods=["GET"],
        ),
    ],
    middleware=[to_starlette_middleware(admin_users_permission_middleware)],
)

admin_products_router = Starlette(
    routes=[
        Route("/", to_starlette(admin_products_list_handler), methods=["GET"]),
        Route("/", to_starlette(admin_product_create_handler), methods=["POST"]),
        Route(
            "/{product_id}", to_starlette(admin_product_update_handler), methods=["PUT"]
        ),
        Route(
            "/{product_id}",
            to_starlette(admin_product_delete_handler),
            methods=["DELETE"],
        ),
        Route(
            "/{product_id}/featured",
            to_starlette(admin_product_feature_handler),
            methods=["POST"],
        ),
    ],
    middleware=[to_starlette_middleware(admin_products_permission_middleware)],
)

admin_orders_router = Starlette(
    routes=[
        Route("/", to_starlette(admin_orders_list_handler), methods=["GET"]),
        Route("/{order_id}", to_starlette(admin_order_detail_handler), methods=["GET"]),
        Route(
            "/{order_id}/status",
            to_starlette(admin_order_status_handler),
            methods=["PUT"],
        ),
        Route(
            "/{order_id}/refund",
            to_starlette(admin_order_refund_handler),
            methods=["POST"],
        ),
    ],
    middleware=[to_starlette_middleware(admin_orders_permission_middleware)],
)

admin_analytics_routes = [
    Route("/", to_starlette(admin_analytics_handler), methods=["GET"]),
    Route("/revenue", to_starlette(admin_analytics_revenue_handler), methods=["GET"]),
    Route("/users", to_starlette(admin_analytics_users_handler), methods=["GET"]),
    Route("/products", to_starlette(admin_analytics_products_handler), methods=["GET"]),
]

admin_router = Starlette(
    routes=[
        Route("/", to_starlette(admin_dashboard_handler), methods=["GET"]),
        Route("/settings", to_starlette(admin_settings_handler), methods=["GET"]),
        Route(
            "/settings", to_starlette(admin_settings_update_handler), methods=["PUT"]
        ),
        Route("/logs", to_starlette(admin_logs_handler), methods=["GET"]),
        Route(
            "/logs/{log_id}", to_starlette(admin_log_detail_handler), methods=["GET"]
        ),
        Mount("/users", admin_users_router),
        Mount("/products", admin_products_router),
        Mount("/orders", admin_orders_router),
        Mount("/analytics", routes=admin_analytics_routes),
    ],
    middleware=[
        to_starlette_middleware(admin_auth_middleware),
        to_starlette_middleware(admin_logging_middleware),
    ],
    exception_handlers={
        404: to_starlette_exc(admin_not_found_handler, 404),
        405: to_starlette_exc(admin_method_not_allowed_handler, 405),
    },
)

root_router = Starlette(
    routes=[
        Route("/", to_starlette(home_handler), methods=["GET"]),
        Route("/about", to_starlette(about_handler), methods=["GET"]),
        Route("/contact", to_starlette(contact_handler), methods=["GET"]),
        Route("/contact", to_starlette(contact_submit_handler), methods=["POST"]),
        Route("/pricing", to_starlette(pricing_handler), methods=["GET"]),
        Mount("/static", static_router),
        Mount("/uploads", routes=uploads_routes),
        Mount("/auth", auth_router),
        Mount("/user", user_router),
        Mount("/dashboard", dashboard_router),
        Mount("/products", products_router),
        Mount("/orders", orders_router),
        Mount("/cart", cart_router),
        Mount("/payments", payments_router),
        Mount("/api/v1", api_v1_router),
        Mount("/admin", admin_router),
    ],
    middleware=[
        to_starlette_middleware(logging_middleware),
        to_starlette_middleware(cors_middleware),
    ],
    exception_handlers={
        404: to_starlette_exc(not_found_handler, 404),
        405: to_starlette_exc(method_not_allowed_handler, 405),
    },
)
