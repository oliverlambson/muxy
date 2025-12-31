"""
To run app:
    uv run granian benchmarks.app.fastapi:root_router --loop uvloop --interface asgi --port 8082
"""

from functools import wraps
from typing import TYPE_CHECKING

from fastapi import APIRouter, FastAPI
from fastapi.responses import PlainTextResponse
from starlette.middleware import Middleware

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


def to_fastapi(
    h: Callable[[], str], code: int = 200
) -> Callable[[], Awaitable[PlainTextResponse]]:
    @wraps(h)
    async def handler() -> PlainTextResponse:
        return PlainTextResponse(h(), status_code=code)

    return handler


def to_fastapi_exc(
    h: Callable[[], str], code: int
) -> Callable[[Request, Exception], Awaitable[PlainTextResponse]]:
    @wraps(h)
    async def handler(r: Request, e: Exception) -> PlainTextResponse:
        return PlainTextResponse(h(), status_code=code)

    return handler


def to_fastapi_middleware[T](m: Callable[[T], T]) -> Middleware:
    @wraps(m)
    def middleware_factory(app):
        return m(app)

    return Middleware(middleware_factory)


# static router - needs custom 405 handler
static_app = FastAPI()
static_router = APIRouter()
static_router.add_api_route("/{path:path}", to_fastapi(static_handler), methods=["GET"])
static_app.include_router(static_router)
static_app.add_exception_handler(
    405, to_fastapi_exc(static_method_not_allowed_handler, 405)
)

# uploads router - simple, no middleware/exception handlers
uploads_router = APIRouter()
uploads_router.add_api_route(
    "/{path:path}", to_fastapi(uploads_handler), methods=["GET"]
)

# auth router
auth_app = FastAPI(middleware=[to_fastapi_middleware(auth_rate_limit_middleware)])
auth_router = APIRouter()
auth_router.add_api_route("/login", to_fastapi(auth_login_handler), methods=["POST"])
auth_router.add_api_route("/logout", to_fastapi(auth_logout_handler), methods=["POST"])
auth_router.add_api_route(
    "/register", to_fastapi(auth_register_handler), methods=["POST"]
)
auth_router.add_api_route(
    "/password/reset", to_fastapi(auth_password_reset_handler), methods=["POST"]
)
auth_router.add_api_route(
    "/password/change", to_fastapi(auth_password_change_handler), methods=["POST"]
)
auth_router.add_api_route(
    "/verify/{token}", to_fastapi(auth_verify_handler), methods=["GET"]
)
auth_app.include_router(auth_router)

# user router
user_app = FastAPI(
    middleware=[
        to_fastapi_middleware(user_auth_middleware),
        to_fastapi_middleware(session_middleware),
    ]
)
user_router = APIRouter()
user_router.add_api_route("/profile", to_fastapi(user_profile_handler), methods=["GET"])
user_router.add_api_route(
    "/profile", to_fastapi(user_profile_update_handler), methods=["PUT"]
)
user_router.add_api_route(
    "/account", to_fastapi(user_account_delete_handler), methods=["DELETE"]
)
user_router.add_api_route(
    "/settings", to_fastapi(user_settings_handler), methods=["GET"]
)
user_router.add_api_route(
    "/settings", to_fastapi(user_settings_update_handler), methods=["POST"]
)
user_router.add_api_route(
    "/notifications", to_fastapi(user_notifications_handler), methods=["GET"]
)
user_router.add_api_route(
    "/notifications/{notification_id}",
    to_fastapi(user_notification_update_handler),
    methods=["PUT"],
)
user_app.include_router(user_router)

# dashboard router
dashboard_app = FastAPI(middleware=[to_fastapi_middleware(user_auth_middleware)])
dashboard_router = APIRouter()
dashboard_router.add_api_route("/", to_fastapi(dashboard_handler), methods=["GET"])
dashboard_router.add_api_route(
    "/stats", to_fastapi(dashboard_stats_handler), methods=["GET"]
)
dashboard_router.add_api_route(
    "/activity", to_fastapi(dashboard_activity_handler), methods=["GET"]
)
dashboard_app.include_router(dashboard_router)

# products router
products_app = FastAPI(middleware=[to_fastapi_middleware(cache_middleware)])
products_router = APIRouter()
products_router.add_api_route("/", to_fastapi(products_list_handler), methods=["GET"])
products_router.add_api_route(
    "/{product_id}", to_fastapi(product_detail_handler), methods=["GET"]
)
products_router.add_api_route("/", to_fastapi(product_create_handler), methods=["POST"])
products_router.add_api_route(
    "/{product_id}", to_fastapi(product_update_handler), methods=["PUT"]
)
products_router.add_api_route(
    "/{product_id}", to_fastapi(product_delete_handler), methods=["DELETE"]
)
products_router.add_api_route(
    "/{product_id}/reviews", to_fastapi(product_reviews_handler), methods=["GET"]
)
products_router.add_api_route(
    "/{product_id}/reviews", to_fastapi(product_review_create_handler), methods=["POST"]
)
products_app.include_router(products_router)

# orders router
orders_app = FastAPI(middleware=[to_fastapi_middleware(user_auth_middleware)])
orders_router = APIRouter()
orders_router.add_api_route("/", to_fastapi(orders_list_handler), methods=["GET"])
orders_router.add_api_route(
    "/{order_id}", to_fastapi(order_detail_handler), methods=["GET"]
)
orders_router.add_api_route("/", to_fastapi(order_create_handler), methods=["POST"])
orders_router.add_api_route(
    "/{order_id}/cancel", to_fastapi(order_cancel_handler), methods=["PUT"]
)
orders_router.add_api_route(
    "/{order_id}/invoice", to_fastapi(order_invoice_handler), methods=["GET"]
)
orders_app.include_router(orders_router)

# cart router
cart_app = FastAPI(middleware=[to_fastapi_middleware(session_middleware)])
cart_router = APIRouter()
cart_router.add_api_route("/", to_fastapi(cart_view_handler), methods=["GET"])
cart_router.add_api_route("/items", to_fastapi(cart_add_item_handler), methods=["POST"])
cart_router.add_api_route(
    "/items/{item_id}", to_fastapi(cart_update_item_handler), methods=["PUT"]
)
cart_router.add_api_route(
    "/items/{item_id}", to_fastapi(cart_remove_item_handler), methods=["DELETE"]
)
cart_router.add_api_route(
    "/checkout", to_fastapi(cart_checkout_handler), methods=["POST"]
)
cart_app.include_router(cart_router)

# payments router
payments_app = FastAPI(
    middleware=[
        to_fastapi_middleware(user_auth_middleware),
        to_fastapi_middleware(payment_security_middleware),
    ]
)
payments_router = APIRouter()
payments_router.add_api_route(
    "/process", to_fastapi(payment_process_handler), methods=["POST"]
)
payments_router.add_api_route(
    "/{payment_id}/status", to_fastapi(payment_status_handler), methods=["GET"]
)
payments_router.add_api_route(
    "/{payment_id}/refund", to_fastapi(payment_refund_handler), methods=["POST"]
)
payments_app.include_router(payments_router)

# api sub-routers (no middleware, just routes)
api_products_router = APIRouter()
api_products_router.add_api_route(
    "/", to_fastapi(api_products_handler), methods=["GET"]
)
api_products_router.add_api_route(
    "/{product_id}", to_fastapi(api_product_handler), methods=["GET"]
)
api_products_router.add_api_route(
    "/{product_id}/reviews", to_fastapi(api_product_review_handler), methods=["POST"]
)
api_products_router.add_api_route(
    "/{product_id}/reviews/{review_id}",
    to_fastapi(api_product_review_detail_handler),
    methods=["GET"],
)

api_orders_router = APIRouter()
api_orders_router.add_api_route("/", to_fastapi(api_orders_handler), methods=["GET"])
api_orders_router.add_api_route(
    "/{order_id}", to_fastapi(api_order_handler), methods=["GET"]
)

api_user_router = APIRouter()
api_user_router.add_api_route(
    "/profile", to_fastapi(api_user_profile_handler), methods=["GET"]
)

# api v1 router
api_v1_app = FastAPI(
    middleware=[
        to_fastapi_middleware(rate_limit_middleware),
        to_fastapi_middleware(api_auth_middleware),
    ]
)
api_v1_router = APIRouter()
api_v1_router.add_api_route("/health", to_fastapi(api_health_handler), methods=["GET"])
api_v1_router.add_api_route("/status", to_fastapi(api_status_handler), methods=["GET"])
api_v1_app.include_router(api_v1_router)
api_v1_app.include_router(api_products_router, prefix="/products")
api_v1_app.include_router(api_orders_router, prefix="/orders")
api_v1_app.include_router(api_user_router, prefix="/user")
api_v1_app.add_exception_handler(404, to_fastapi_exc(api_not_found_handler, 404))
api_v1_app.add_exception_handler(
    405, to_fastapi_exc(api_method_not_allowed_handler, 405)
)

# admin sub-routers
admin_users_app = FastAPI(
    middleware=[to_fastapi_middleware(admin_users_permission_middleware)]
)
admin_users_router = APIRouter()
admin_users_router.add_api_route(
    "/", to_fastapi(admin_users_list_handler), methods=["GET"]
)
admin_users_router.add_api_route(
    "/{user_id}", to_fastapi(admin_user_detail_handler), methods=["GET"]
)
admin_users_router.add_api_route(
    "/{user_id}", to_fastapi(admin_user_update_handler), methods=["PUT"]
)
admin_users_router.add_api_route(
    "/{user_id}", to_fastapi(admin_user_delete_handler), methods=["DELETE"]
)
admin_users_router.add_api_route(
    "/{user_id}/suspend", to_fastapi(admin_user_suspend_handler), methods=["POST"]
)
admin_users_router.add_api_route(
    "/{user_id}/activate", to_fastapi(admin_user_activate_handler), methods=["POST"]
)
admin_users_router.add_api_route(
    "/{user_id}/activity", to_fastapi(admin_user_activity_handler), methods=["GET"]
)
admin_users_router.add_api_route(
    "/{user_id}/orders", to_fastapi(admin_user_orders_handler), methods=["GET"]
)
admin_users_router.add_api_route(
    "/{user_id}/orders/{order_id}",
    to_fastapi(admin_user_order_detail_handler),
    methods=["GET"],
)
admin_users_app.include_router(admin_users_router)

admin_products_app = FastAPI(
    middleware=[to_fastapi_middleware(admin_products_permission_middleware)]
)
admin_products_router = APIRouter()
admin_products_router.add_api_route(
    "/", to_fastapi(admin_products_list_handler), methods=["GET"]
)
admin_products_router.add_api_route(
    "/", to_fastapi(admin_product_create_handler), methods=["POST"]
)
admin_products_router.add_api_route(
    "/{product_id}", to_fastapi(admin_product_update_handler), methods=["PUT"]
)
admin_products_router.add_api_route(
    "/{product_id}", to_fastapi(admin_product_delete_handler), methods=["DELETE"]
)
admin_products_router.add_api_route(
    "/{product_id}/featured",
    to_fastapi(admin_product_feature_handler),
    methods=["POST"],
)
admin_products_app.include_router(admin_products_router)

admin_orders_app = FastAPI(
    middleware=[to_fastapi_middleware(admin_orders_permission_middleware)]
)
admin_orders_router = APIRouter()
admin_orders_router.add_api_route(
    "/", to_fastapi(admin_orders_list_handler), methods=["GET"]
)
admin_orders_router.add_api_route(
    "/{order_id}", to_fastapi(admin_order_detail_handler), methods=["GET"]
)
admin_orders_router.add_api_route(
    "/{order_id}/status", to_fastapi(admin_order_status_handler), methods=["PUT"]
)
admin_orders_router.add_api_route(
    "/{order_id}/refund", to_fastapi(admin_order_refund_handler), methods=["POST"]
)
admin_orders_app.include_router(admin_orders_router)

# admin analytics - no middleware
admin_analytics_router = APIRouter()
admin_analytics_router.add_api_route(
    "/", to_fastapi(admin_analytics_handler), methods=["GET"]
)
admin_analytics_router.add_api_route(
    "/revenue", to_fastapi(admin_analytics_revenue_handler), methods=["GET"]
)
admin_analytics_router.add_api_route(
    "/users", to_fastapi(admin_analytics_users_handler), methods=["GET"]
)
admin_analytics_router.add_api_route(
    "/products", to_fastapi(admin_analytics_products_handler), methods=["GET"]
)

# admin router
admin_app = FastAPI(
    middleware=[
        to_fastapi_middleware(admin_auth_middleware),
        to_fastapi_middleware(admin_logging_middleware),
    ]
)
admin_main_router = APIRouter()
admin_main_router.add_api_route(
    "/", to_fastapi(admin_dashboard_handler), methods=["GET"]
)
admin_main_router.add_api_route(
    "/settings", to_fastapi(admin_settings_handler), methods=["GET"]
)
admin_main_router.add_api_route(
    "/settings", to_fastapi(admin_settings_update_handler), methods=["PUT"]
)
admin_main_router.add_api_route(
    "/logs", to_fastapi(admin_logs_handler), methods=["GET"]
)
admin_main_router.add_api_route(
    "/logs/{log_id}", to_fastapi(admin_log_detail_handler), methods=["GET"]
)
admin_app.include_router(admin_main_router)
admin_app.mount("/users", admin_users_app)
admin_app.mount("/products", admin_products_app)
admin_app.mount("/orders", admin_orders_app)
admin_app.include_router(admin_analytics_router, prefix="/analytics")
admin_app.add_exception_handler(404, to_fastapi_exc(admin_not_found_handler, 404))
admin_app.add_exception_handler(
    405, to_fastapi_exc(admin_method_not_allowed_handler, 405)
)

# root router
root_router = FastAPI(
    middleware=[
        to_fastapi_middleware(logging_middleware),
        to_fastapi_middleware(cors_middleware),
    ]
)
main_router = APIRouter()
main_router.add_api_route("/", to_fastapi(home_handler), methods=["GET"])
main_router.add_api_route("/about", to_fastapi(about_handler), methods=["GET"])
main_router.add_api_route("/contact", to_fastapi(contact_handler), methods=["GET"])
main_router.add_api_route(
    "/contact", to_fastapi(contact_submit_handler), methods=["POST"]
)
main_router.add_api_route("/pricing", to_fastapi(pricing_handler), methods=["GET"])
root_router.include_router(main_router)
root_router.mount("/static", static_app)
root_router.include_router(uploads_router, prefix="/uploads")
root_router.mount("/auth", auth_app)
root_router.mount("/user", user_app)
root_router.mount("/dashboard", dashboard_app)
root_router.mount("/products", products_app)
root_router.mount("/orders", orders_app)
root_router.mount("/cart", cart_app)
root_router.mount("/payments", payments_app)
root_router.mount("/api/v1", api_v1_app)
root_router.mount("/admin", admin_app)
root_router.add_exception_handler(404, to_fastapi_exc(not_found_handler, 404))
root_router.add_exception_handler(405, to_fastapi_exc(method_not_allowed_handler, 405))
