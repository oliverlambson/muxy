"""
To run app:
    uv run granian benchmarks.app.litestar:root_router --loop uvloop --interface asgi --port 8083
"""

from typing import TYPE_CHECKING

from litestar import Litestar, Request, Router
from litestar.exceptions import MethodNotAllowedException, NotFoundException
from litestar.handlers import delete, get, post, put
from litestar.middleware import AbstractMiddleware
from litestar.response import Response

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
    from collections.abc import Callable

    from litestar.types import Receive, Scope, Send


def to_litestar_middleware[T](m: Callable[[T], T]) -> type[AbstractMiddleware]:
    """Convert no-op middleware to Litestar middleware class."""

    class NoOpMiddleware(AbstractMiddleware):
        async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
            await self.app(scope, receive, send)

    return NoOpMiddleware


# Static router - has custom 405 handler
@get("/{path:path}")
async def static_route(path: str) -> Response[str]:
    return Response(content=static_handler(), media_type="text/plain")


def static_method_not_allowed_exc_handler(
    request: Request, exc: Exception
) -> Response[str]:
    return Response(
        content=static_method_not_allowed_handler(),
        status_code=405,
        media_type="text/plain",
    )


static_router = Router(
    path="/static",
    route_handlers=[static_route],
    exception_handlers={
        MethodNotAllowedException: static_method_not_allowed_exc_handler
    },
)


# Uploads router
@get("/{path:path}")
async def uploads_route(path: str) -> Response[str]:
    return Response(content=uploads_handler(), media_type="text/plain")


uploads_router = Router(
    path="/uploads",
    route_handlers=[uploads_route],
)


# Auth router
@post("/login")
async def auth_login_route() -> Response[str]:
    return Response(content=auth_login_handler(), media_type="text/plain")


@post("/logout")
async def auth_logout_route() -> Response[str]:
    return Response(content=auth_logout_handler(), media_type="text/plain")


@post("/register")
async def auth_register_route() -> Response[str]:
    return Response(content=auth_register_handler(), media_type="text/plain")


@post("/password/reset")
async def auth_password_reset_route() -> Response[str]:
    return Response(content=auth_password_reset_handler(), media_type="text/plain")


@post("/password/change")
async def auth_password_change_route() -> Response[str]:
    return Response(content=auth_password_change_handler(), media_type="text/plain")


@get("/verify/{token:str}")
async def auth_verify_route(token: str) -> Response[str]:
    return Response(content=auth_verify_handler(), media_type="text/plain")


auth_router = Router(
    path="/auth",
    route_handlers=[
        auth_login_route,
        auth_logout_route,
        auth_register_route,
        auth_password_reset_route,
        auth_password_change_route,
        auth_verify_route,
    ],
    middleware=[to_litestar_middleware(auth_rate_limit_middleware)],
)


# User router
@get("/profile", name="user_profile")
async def user_profile_route() -> Response[str]:
    return Response(content=user_profile_handler(), media_type="text/plain")


@put("/profile", name="user_profile_update")
async def user_profile_update_route() -> Response[str]:
    return Response(content=user_profile_update_handler(), media_type="text/plain")


@delete("/account", status_code=200)
async def user_account_delete_route() -> Response[str]:
    return Response(content=user_account_delete_handler(), media_type="text/plain")


@get("/settings", name="user_settings")
async def user_settings_route() -> Response[str]:
    return Response(content=user_settings_handler(), media_type="text/plain")


@post("/settings", name="user_settings_update")
async def user_settings_update_route() -> Response[str]:
    return Response(content=user_settings_update_handler(), media_type="text/plain")


@get("/notifications")
async def user_notifications_route() -> Response[str]:
    return Response(content=user_notifications_handler(), media_type="text/plain")


@put("/notifications/{notification_id:str}")
async def user_notification_update_route(notification_id: str) -> Response[str]:
    return Response(content=user_notification_update_handler(), media_type="text/plain")


user_router = Router(
    path="/user",
    route_handlers=[
        user_profile_route,
        user_profile_update_route,
        user_account_delete_route,
        user_settings_route,
        user_settings_update_route,
        user_notifications_route,
        user_notification_update_route,
    ],
    middleware=[
        to_litestar_middleware(user_auth_middleware),
        to_litestar_middleware(session_middleware),
    ],
)


# Dashboard router
@get("/", name="dashboard_index")
async def dashboard_index_route() -> Response[str]:
    return Response(content=dashboard_handler(), media_type="text/plain")


@get("/stats")
async def dashboard_stats_route() -> Response[str]:
    return Response(content=dashboard_stats_handler(), media_type="text/plain")


@get("/activity")
async def dashboard_activity_route() -> Response[str]:
    return Response(content=dashboard_activity_handler(), media_type="text/plain")


dashboard_router = Router(
    path="/dashboard",
    route_handlers=[
        dashboard_index_route,
        dashboard_stats_route,
        dashboard_activity_route,
    ],
    middleware=[to_litestar_middleware(user_auth_middleware)],
)


# Products router
@get("/", name="products_list")
async def products_list_route() -> Response[str]:
    return Response(content=products_list_handler(), media_type="text/plain")


@get("/{product_id:str}", name="product_detail")
async def product_detail_route(product_id: str) -> Response[str]:
    return Response(content=product_detail_handler(), media_type="text/plain")


@post("/", name="product_create")
async def product_create_route() -> Response[str]:
    return Response(content=product_create_handler(), media_type="text/plain")


@put("/{product_id:str}", name="product_update")
async def product_update_route(product_id: str) -> Response[str]:
    return Response(content=product_update_handler(), media_type="text/plain")


@delete("/{product_id:str}", name="product_delete", status_code=200)
async def product_delete_route(product_id: str) -> Response[str]:
    return Response(content=product_delete_handler(), media_type="text/plain")


@get("/{product_id:str}/reviews", name="product_reviews")
async def product_reviews_route(product_id: str) -> Response[str]:
    return Response(content=product_reviews_handler(), media_type="text/plain")


@post("/{product_id:str}/reviews", name="product_review_create")
async def product_review_create_route(product_id: str) -> Response[str]:
    return Response(content=product_review_create_handler(), media_type="text/plain")


products_router = Router(
    path="/products",
    route_handlers=[
        products_list_route,
        product_detail_route,
        product_create_route,
        product_update_route,
        product_delete_route,
        product_reviews_route,
        product_review_create_route,
    ],
    middleware=[to_litestar_middleware(cache_middleware)],
)


# Orders router
@get("/", name="orders_list")
async def orders_list_route() -> Response[str]:
    return Response(content=orders_list_handler(), media_type="text/plain")


@get("/{order_id:str}", name="order_detail")
async def order_detail_route(order_id: str) -> Response[str]:
    return Response(content=order_detail_handler(), media_type="text/plain")


@post("/", name="order_create")
async def order_create_route() -> Response[str]:
    return Response(content=order_create_handler(), media_type="text/plain")


@put("/{order_id:str}/cancel")
async def order_cancel_route(order_id: str) -> Response[str]:
    return Response(content=order_cancel_handler(), media_type="text/plain")


@get("/{order_id:str}/invoice")
async def order_invoice_route(order_id: str) -> Response[str]:
    return Response(content=order_invoice_handler(), media_type="text/plain")


orders_router = Router(
    path="/orders",
    route_handlers=[
        orders_list_route,
        order_detail_route,
        order_create_route,
        order_cancel_route,
        order_invoice_route,
    ],
    middleware=[to_litestar_middleware(user_auth_middleware)],
)


# Cart router
@get("/", name="cart_view")
async def cart_view_route() -> Response[str]:
    return Response(content=cart_view_handler(), media_type="text/plain")


@post("/items")
async def cart_add_item_route() -> Response[str]:
    return Response(content=cart_add_item_handler(), media_type="text/plain")


@put("/items/{item_id:str}")
async def cart_update_item_route(item_id: str) -> Response[str]:
    return Response(content=cart_update_item_handler(), media_type="text/plain")


@delete("/items/{item_id:str}", status_code=200)
async def cart_remove_item_route(item_id: str) -> Response[str]:
    return Response(content=cart_remove_item_handler(), media_type="text/plain")


@post("/checkout")
async def cart_checkout_route() -> Response[str]:
    return Response(content=cart_checkout_handler(), media_type="text/plain")


cart_router = Router(
    path="/cart",
    route_handlers=[
        cart_view_route,
        cart_add_item_route,
        cart_update_item_route,
        cart_remove_item_route,
        cart_checkout_route,
    ],
    middleware=[to_litestar_middleware(session_middleware)],
)


# Payments router
@post("/process")
async def payment_process_route() -> Response[str]:
    return Response(content=payment_process_handler(), media_type="text/plain")


@get("/{payment_id:str}/status")
async def payment_status_route(payment_id: str) -> Response[str]:
    return Response(content=payment_status_handler(), media_type="text/plain")


@post("/{payment_id:str}/refund")
async def payment_refund_route(payment_id: str) -> Response[str]:
    return Response(content=payment_refund_handler(), media_type="text/plain")


payments_router = Router(
    path="/payments",
    route_handlers=[payment_process_route, payment_status_route, payment_refund_route],
    middleware=[
        to_litestar_middleware(user_auth_middleware),
        to_litestar_middleware(payment_security_middleware),
    ],
)


# API Products router
@get("/", name="api_products_list")
async def api_products_route() -> Response[str]:
    return Response(content=api_products_handler(), media_type="text/plain")


@get("/{product_id:str}", name="api_product_detail")
async def api_product_route(product_id: str) -> Response[str]:
    return Response(content=api_product_handler(), media_type="text/plain")


@post("/{product_id:str}/reviews", name="api_product_review_create")
async def api_product_review_route(product_id: str) -> Response[str]:
    return Response(content=api_product_review_handler(), media_type="text/plain")


@get("/{product_id:str}/reviews/{review_id:str}")
async def api_product_review_detail_route(
    product_id: str, review_id: str
) -> Response[str]:
    return Response(
        content=api_product_review_detail_handler(), media_type="text/plain"
    )


api_products_router = Router(
    path="/products",
    route_handlers=[
        api_products_route,
        api_product_route,
        api_product_review_route,
        api_product_review_detail_route,
    ],
)


# API Orders router
@get("/", name="api_orders_list")
async def api_orders_route() -> Response[str]:
    return Response(content=api_orders_handler(), media_type="text/plain")


@get("/{order_id:str}", name="api_order_detail")
async def api_order_route(order_id: str) -> Response[str]:
    return Response(content=api_order_handler(), media_type="text/plain")


api_orders_router = Router(
    path="/orders",
    route_handlers=[api_orders_route, api_order_route],
)


# API User router
@get("/profile")
async def api_user_profile_route() -> Response[str]:
    return Response(content=api_user_profile_handler(), media_type="text/plain")


api_user_router = Router(
    path="/user",
    route_handlers=[api_user_profile_route],
)


# API v1 router
@get("/health")
async def api_health_route() -> Response[str]:
    return Response(content=api_health_handler(), media_type="text/plain")


@get("/status")
async def api_status_route() -> Response[str]:
    return Response(content=api_status_handler(), media_type="text/plain")


def api_not_found_exc_handler(request: Request, exc: Exception) -> Response[str]:
    return Response(
        content=api_not_found_handler(),
        status_code=404,
        media_type="text/plain",
    )


def api_method_not_allowed_exc_handler(
    request: Request, exc: Exception
) -> Response[str]:
    return Response(
        content=api_method_not_allowed_handler(),
        status_code=405,
        media_type="text/plain",
    )


api_v1_router = Router(
    path="/api/v1",
    route_handlers=[
        api_health_route,
        api_status_route,
        api_products_router,
        api_orders_router,
        api_user_router,
    ],
    middleware=[
        to_litestar_middleware(rate_limit_middleware),
        to_litestar_middleware(api_auth_middleware),
    ],
    exception_handlers={
        NotFoundException: api_not_found_exc_handler,
        MethodNotAllowedException: api_method_not_allowed_exc_handler,
    },
)


# Admin users router
@get("/", name="admin_users_list")
async def admin_users_list_route() -> Response[str]:
    return Response(content=admin_users_list_handler(), media_type="text/plain")


@get("/{user_id:str}", name="admin_user_detail")
async def admin_user_detail_route(user_id: str) -> Response[str]:
    return Response(content=admin_user_detail_handler(), media_type="text/plain")


@put("/{user_id:str}", name="admin_user_update")
async def admin_user_update_route(user_id: str) -> Response[str]:
    return Response(content=admin_user_update_handler(), media_type="text/plain")


@delete("/{user_id:str}", name="admin_user_delete", status_code=200)
async def admin_user_delete_route(user_id: str) -> Response[str]:
    return Response(content=admin_user_delete_handler(), media_type="text/plain")


@post("/{user_id:str}/suspend")
async def admin_user_suspend_route(user_id: str) -> Response[str]:
    return Response(content=admin_user_suspend_handler(), media_type="text/plain")


@post("/{user_id:str}/activate")
async def admin_user_activate_route(user_id: str) -> Response[str]:
    return Response(content=admin_user_activate_handler(), media_type="text/plain")


@get("/{user_id:str}/activity")
async def admin_user_activity_route(user_id: str) -> Response[str]:
    return Response(content=admin_user_activity_handler(), media_type="text/plain")


@get("/{user_id:str}/orders", name="admin_user_orders")
async def admin_user_orders_route(user_id: str) -> Response[str]:
    return Response(content=admin_user_orders_handler(), media_type="text/plain")


@get("/{user_id:str}/orders/{order_id:str}", name="admin_user_order_detail")
async def admin_user_order_detail_route(user_id: str, order_id: str) -> Response[str]:
    return Response(content=admin_user_order_detail_handler(), media_type="text/plain")


admin_users_router = Router(
    path="/users",
    route_handlers=[
        admin_users_list_route,
        admin_user_detail_route,
        admin_user_update_route,
        admin_user_delete_route,
        admin_user_suspend_route,
        admin_user_activate_route,
        admin_user_activity_route,
        admin_user_orders_route,
        admin_user_order_detail_route,
    ],
    middleware=[to_litestar_middleware(admin_users_permission_middleware)],
)


# Admin products router
@get("/", name="admin_products_list")
async def admin_products_list_route() -> Response[str]:
    return Response(content=admin_products_list_handler(), media_type="text/plain")


@post("/", name="admin_product_create")
async def admin_product_create_route() -> Response[str]:
    return Response(content=admin_product_create_handler(), media_type="text/plain")


@put("/{product_id:str}", name="admin_product_update")
async def admin_product_update_route(product_id: str) -> Response[str]:
    return Response(content=admin_product_update_handler(), media_type="text/plain")


@delete("/{product_id:str}", name="admin_product_delete", status_code=200)
async def admin_product_delete_route(product_id: str) -> Response[str]:
    return Response(content=admin_product_delete_handler(), media_type="text/plain")


@post("/{product_id:str}/featured")
async def admin_product_feature_route(product_id: str) -> Response[str]:
    return Response(content=admin_product_feature_handler(), media_type="text/plain")


admin_products_router = Router(
    path="/products",
    route_handlers=[
        admin_products_list_route,
        admin_product_create_route,
        admin_product_update_route,
        admin_product_delete_route,
        admin_product_feature_route,
    ],
    middleware=[to_litestar_middleware(admin_products_permission_middleware)],
)


# Admin orders router
@get("/", name="admin_orders_list")
async def admin_orders_list_route() -> Response[str]:
    return Response(content=admin_orders_list_handler(), media_type="text/plain")


@get("/{order_id:str}", name="admin_order_detail")
async def admin_order_detail_route(order_id: str) -> Response[str]:
    return Response(content=admin_order_detail_handler(), media_type="text/plain")


@put("/{order_id:str}/status")
async def admin_order_status_route(order_id: str) -> Response[str]:
    return Response(content=admin_order_status_handler(), media_type="text/plain")


@post("/{order_id:str}/refund")
async def admin_order_refund_route(order_id: str) -> Response[str]:
    return Response(content=admin_order_refund_handler(), media_type="text/plain")


admin_orders_router = Router(
    path="/orders",
    route_handlers=[
        admin_orders_list_route,
        admin_order_detail_route,
        admin_order_status_route,
        admin_order_refund_route,
    ],
    middleware=[to_litestar_middleware(admin_orders_permission_middleware)],
)


# Admin analytics router
@get("/", name="admin_analytics")
async def admin_analytics_route() -> Response[str]:
    return Response(content=admin_analytics_handler(), media_type="text/plain")


@get("/revenue")
async def admin_analytics_revenue_route() -> Response[str]:
    return Response(content=admin_analytics_revenue_handler(), media_type="text/plain")


@get("/users", name="admin_analytics_users")
async def admin_analytics_users_route() -> Response[str]:
    return Response(content=admin_analytics_users_handler(), media_type="text/plain")


@get("/products", name="admin_analytics_products")
async def admin_analytics_products_route() -> Response[str]:
    return Response(content=admin_analytics_products_handler(), media_type="text/plain")


admin_analytics_router = Router(
    path="/analytics",
    route_handlers=[
        admin_analytics_route,
        admin_analytics_revenue_route,
        admin_analytics_users_route,
        admin_analytics_products_route,
    ],
)


# Admin router
@get("/", name="admin_dashboard")
async def admin_dashboard_route() -> Response[str]:
    return Response(content=admin_dashboard_handler(), media_type="text/plain")


@get("/settings", name="admin_settings")
async def admin_settings_route() -> Response[str]:
    return Response(content=admin_settings_handler(), media_type="text/plain")


@put("/settings", name="admin_settings_update")
async def admin_settings_update_route() -> Response[str]:
    return Response(content=admin_settings_update_handler(), media_type="text/plain")


@get("/logs")
async def admin_logs_route() -> Response[str]:
    return Response(content=admin_logs_handler(), media_type="text/plain")


@get("/logs/{log_id:str}")
async def admin_log_detail_route(log_id: str) -> Response[str]:
    return Response(content=admin_log_detail_handler(), media_type="text/plain")


def admin_not_found_exc_handler(request: Request, exc: Exception) -> Response[str]:
    return Response(
        content=admin_not_found_handler(),
        status_code=404,
        media_type="text/plain",
    )


def admin_method_not_allowed_exc_handler(
    request: Request, exc: Exception
) -> Response[str]:
    return Response(
        content=admin_method_not_allowed_handler(),
        status_code=405,
        media_type="text/plain",
    )


admin_router = Router(
    path="/admin",
    route_handlers=[
        admin_dashboard_route,
        admin_settings_route,
        admin_settings_update_route,
        admin_logs_route,
        admin_log_detail_route,
        admin_users_router,
        admin_products_router,
        admin_orders_router,
        admin_analytics_router,
    ],
    middleware=[
        to_litestar_middleware(admin_auth_middleware),
        to_litestar_middleware(admin_logging_middleware),
    ],
    exception_handlers={
        NotFoundException: admin_not_found_exc_handler,
        MethodNotAllowedException: admin_method_not_allowed_exc_handler,
    },
)


# Root handlers
@get("/", name="home")
async def home_route() -> Response[str]:
    return Response(content=home_handler(), media_type="text/plain")


@get("/about")
async def about_route() -> Response[str]:
    return Response(content=about_handler(), media_type="text/plain")


@get("/contact", name="contact_get")
async def contact_route() -> Response[str]:
    return Response(content=contact_handler(), media_type="text/plain")


@post("/contact", name="contact_post")
async def contact_submit_route() -> Response[str]:
    return Response(content=contact_submit_handler(), media_type="text/plain")


@get("/pricing")
async def pricing_route() -> Response[str]:
    return Response(content=pricing_handler(), media_type="text/plain")


def root_not_found_exc_handler(request: Request, exc: Exception) -> Response[str]:
    return Response(
        content=not_found_handler(),
        status_code=404,
        media_type="text/plain",
    )


def root_method_not_allowed_exc_handler(
    request: Request, exc: Exception
) -> Response[str]:
    return Response(
        content=method_not_allowed_handler(),
        status_code=405,
        media_type="text/plain",
    )


# Root application
root_router = Litestar(
    route_handlers=[
        home_route,
        about_route,
        contact_route,
        contact_submit_route,
        pricing_route,
        static_router,
        uploads_router,
        auth_router,
        user_router,
        dashboard_router,
        products_router,
        orders_router,
        cart_router,
        payments_router,
        api_v1_router,
        admin_router,
    ],
    middleware=[
        to_litestar_middleware(logging_middleware),
        to_litestar_middleware(cors_middleware),
    ],
    exception_handlers={
        NotFoundException: root_not_found_exc_handler,
        MethodNotAllowedException: root_method_not_allowed_exc_handler,
    },
)
