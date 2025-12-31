"""
To run app:
    uv run sanic benchmarks.app.sanic:root_router --port 8084 --single-process
"""

from functools import wraps
from typing import TYPE_CHECKING

from sanic import Blueprint, Request, Sanic
from sanic.response import HTTPResponse, text

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


def to_sanic(
    h: Callable[[], str], code: int = 200
) -> Callable[[Request], Awaitable[HTTPResponse]]:
    @wraps(h)
    async def handler(r: Request) -> HTTPResponse:
        return text(h(), status=code)

    return handler


def to_sanic_middleware[T](m: Callable[[T], T]) -> Callable[[Request], Awaitable[None]]:
    @wraps(m)
    async def middleware(r: Request) -> None:
        pass

    return middleware


# static blueprint
static_bp = Blueprint("static", url_prefix="/static")


@static_bp.get("/<path:path>")
async def static_route(r: Request, path: str) -> HTTPResponse:
    return text(static_handler())


@static_bp.exception(Exception)
async def static_exception(r: Request, e: Exception) -> HTTPResponse:
    if hasattr(e, "status_code") and e.status_code == 405:
        return text(static_method_not_allowed_handler(), status=405)
    raise e


# uploads blueprint
uploads_bp = Blueprint("uploads", url_prefix="/uploads")


@uploads_bp.get("/<path:path>")
async def uploads_route(r: Request, path: str) -> HTTPResponse:
    return text(uploads_handler())


# auth blueprint
auth_bp = Blueprint("auth", url_prefix="/auth")
auth_bp.on_request(to_sanic_middleware(auth_rate_limit_middleware))


@auth_bp.post("/login")
async def auth_login_route(r: Request) -> HTTPResponse:
    return text(auth_login_handler())


@auth_bp.post("/logout")
async def auth_logout_route(r: Request) -> HTTPResponse:
    return text(auth_logout_handler())


@auth_bp.post("/register")
async def auth_register_route(r: Request) -> HTTPResponse:
    return text(auth_register_handler())


@auth_bp.post("/password/reset")
async def auth_password_reset_route(r: Request) -> HTTPResponse:
    return text(auth_password_reset_handler())


@auth_bp.post("/password/change")
async def auth_password_change_route(r: Request) -> HTTPResponse:
    return text(auth_password_change_handler())


@auth_bp.get("/verify/<token>")
async def auth_verify_route(r: Request, token: str) -> HTTPResponse:
    return text(auth_verify_handler())


# user blueprint
user_bp = Blueprint("user", url_prefix="/user")
user_bp.on_request(to_sanic_middleware(user_auth_middleware))
user_bp.on_request(to_sanic_middleware(session_middleware))


@user_bp.get("/profile")
async def user_profile_route(r: Request) -> HTTPResponse:
    return text(user_profile_handler())


@user_bp.put("/profile")
async def user_profile_update_route(r: Request) -> HTTPResponse:
    return text(user_profile_update_handler())


@user_bp.delete("/account")
async def user_account_delete_route(r: Request) -> HTTPResponse:
    return text(user_account_delete_handler())


@user_bp.get("/settings")
async def user_settings_route(r: Request) -> HTTPResponse:
    return text(user_settings_handler())


@user_bp.post("/settings")
async def user_settings_update_route(r: Request) -> HTTPResponse:
    return text(user_settings_update_handler())


@user_bp.get("/notifications")
async def user_notifications_route(r: Request) -> HTTPResponse:
    return text(user_notifications_handler())


@user_bp.put("/notifications/<notification_id>")
async def user_notification_update_route(
    r: Request, notification_id: str
) -> HTTPResponse:
    return text(user_notification_update_handler())


# dashboard blueprint
dashboard_bp = Blueprint("dashboard", url_prefix="/dashboard")
dashboard_bp.on_request(to_sanic_middleware(user_auth_middleware))


@dashboard_bp.get("/")
async def dashboard_route(r: Request) -> HTTPResponse:
    return text(dashboard_handler())


@dashboard_bp.get("/stats")
async def dashboard_stats_route(r: Request) -> HTTPResponse:
    return text(dashboard_stats_handler())


@dashboard_bp.get("/activity")
async def dashboard_activity_route(r: Request) -> HTTPResponse:
    return text(dashboard_activity_handler())


# products blueprint
products_bp = Blueprint("products", url_prefix="/products")
products_bp.on_request(to_sanic_middleware(cache_middleware))


@products_bp.get("/")
async def products_list_route(r: Request) -> HTTPResponse:
    return text(products_list_handler())


@products_bp.get("/<product_id>")
async def product_detail_route(r: Request, product_id: str) -> HTTPResponse:
    return text(product_detail_handler())


@products_bp.post("/")
async def product_create_route(r: Request) -> HTTPResponse:
    return text(product_create_handler())


@products_bp.put("/<product_id>")
async def product_update_route(r: Request, product_id: str) -> HTTPResponse:
    return text(product_update_handler())


@products_bp.delete("/<product_id>")
async def product_delete_route(r: Request, product_id: str) -> HTTPResponse:
    return text(product_delete_handler())


@products_bp.get("/<product_id>/reviews")
async def product_reviews_route(r: Request, product_id: str) -> HTTPResponse:
    return text(product_reviews_handler())


@products_bp.post("/<product_id>/reviews")
async def product_review_create_route(r: Request, product_id: str) -> HTTPResponse:
    return text(product_review_create_handler())


# orders blueprint
orders_bp = Blueprint("orders", url_prefix="/orders")
orders_bp.on_request(to_sanic_middleware(user_auth_middleware))


@orders_bp.get("/")
async def orders_list_route(r: Request) -> HTTPResponse:
    return text(orders_list_handler())


@orders_bp.get("/<order_id>")
async def order_detail_route(r: Request, order_id: str) -> HTTPResponse:
    return text(order_detail_handler())


@orders_bp.post("/")
async def order_create_route(r: Request) -> HTTPResponse:
    return text(order_create_handler())


@orders_bp.put("/<order_id>/cancel")
async def order_cancel_route(r: Request, order_id: str) -> HTTPResponse:
    return text(order_cancel_handler())


@orders_bp.get("/<order_id>/invoice")
async def order_invoice_route(r: Request, order_id: str) -> HTTPResponse:
    return text(order_invoice_handler())


# cart blueprint
cart_bp = Blueprint("cart", url_prefix="/cart")
cart_bp.on_request(to_sanic_middleware(session_middleware))


@cart_bp.get("/")
async def cart_view_route(r: Request) -> HTTPResponse:
    return text(cart_view_handler())


@cart_bp.post("/items")
async def cart_add_item_route(r: Request) -> HTTPResponse:
    return text(cart_add_item_handler())


@cart_bp.put("/items/<item_id>")
async def cart_update_item_route(r: Request, item_id: str) -> HTTPResponse:
    return text(cart_update_item_handler())


@cart_bp.delete("/items/<item_id>")
async def cart_remove_item_route(r: Request, item_id: str) -> HTTPResponse:
    return text(cart_remove_item_handler())


@cart_bp.post("/checkout")
async def cart_checkout_route(r: Request) -> HTTPResponse:
    return text(cart_checkout_handler())


# payments blueprint
payments_bp = Blueprint("payments", url_prefix="/payments")
payments_bp.on_request(to_sanic_middleware(user_auth_middleware))
payments_bp.on_request(to_sanic_middleware(payment_security_middleware))


@payments_bp.post("/process")
async def payment_process_route(r: Request) -> HTTPResponse:
    return text(payment_process_handler())


@payments_bp.get("/<payment_id>/status")
async def payment_status_route(r: Request, payment_id: str) -> HTTPResponse:
    return text(payment_status_handler())


@payments_bp.post("/<payment_id>/refund")
async def payment_refund_route(r: Request, payment_id: str) -> HTTPResponse:
    return text(payment_refund_handler())


# api/v1 blueprints
api_products_bp = Blueprint("api_products", url_prefix="/products")


@api_products_bp.get("/")
async def api_products_route(r: Request) -> HTTPResponse:
    return text(api_products_handler())


@api_products_bp.get("/<product_id>")
async def api_product_route(r: Request, product_id: str) -> HTTPResponse:
    return text(api_product_handler())


@api_products_bp.post("/<product_id>/reviews")
async def api_product_review_route(r: Request, product_id: str) -> HTTPResponse:
    return text(api_product_review_handler())


@api_products_bp.get("/<product_id>/reviews/<review_id>")
async def api_product_review_detail_route(
    r: Request, product_id: str, review_id: str
) -> HTTPResponse:
    return text(api_product_review_detail_handler())


api_orders_bp = Blueprint("api_orders", url_prefix="/orders")


@api_orders_bp.get("/")
async def api_orders_route(r: Request) -> HTTPResponse:
    return text(api_orders_handler())


@api_orders_bp.get("/<order_id>")
async def api_order_route(r: Request, order_id: str) -> HTTPResponse:
    return text(api_order_handler())


api_user_bp = Blueprint("api_user", url_prefix="/user")


@api_user_bp.get("/profile")
async def api_user_profile_route(r: Request) -> HTTPResponse:
    return text(api_user_profile_handler())


api_v1_group = Blueprint.group(
    api_products_bp, api_orders_bp, api_user_bp, url_prefix="/api/v1"
)


# Create a blueprint for the /api/v1 level routes and middleware
api_v1_bp = Blueprint("api_v1", url_prefix="/api/v1")
api_v1_bp.on_request(to_sanic_middleware(rate_limit_middleware))
api_v1_bp.on_request(to_sanic_middleware(api_auth_middleware))


@api_v1_bp.get("/health")
async def api_health_route(r: Request) -> HTTPResponse:
    return text(api_health_handler())


@api_v1_bp.get("/status")
async def api_status_route(r: Request) -> HTTPResponse:
    return text(api_status_handler())


# admin blueprints
admin_users_bp = Blueprint("admin_users", url_prefix="/users")
admin_users_bp.on_request(to_sanic_middleware(admin_users_permission_middleware))


@admin_users_bp.get("/")
async def admin_users_list_route(r: Request) -> HTTPResponse:
    return text(admin_users_list_handler())


@admin_users_bp.get("/<user_id>")
async def admin_user_detail_route(r: Request, user_id: str) -> HTTPResponse:
    return text(admin_user_detail_handler())


@admin_users_bp.put("/<user_id>")
async def admin_user_update_route(r: Request, user_id: str) -> HTTPResponse:
    return text(admin_user_update_handler())


@admin_users_bp.delete("/<user_id>")
async def admin_user_delete_route(r: Request, user_id: str) -> HTTPResponse:
    return text(admin_user_delete_handler())


@admin_users_bp.post("/<user_id>/suspend")
async def admin_user_suspend_route(r: Request, user_id: str) -> HTTPResponse:
    return text(admin_user_suspend_handler())


@admin_users_bp.post("/<user_id>/activate")
async def admin_user_activate_route(r: Request, user_id: str) -> HTTPResponse:
    return text(admin_user_activate_handler())


@admin_users_bp.get("/<user_id>/activity")
async def admin_user_activity_route(r: Request, user_id: str) -> HTTPResponse:
    return text(admin_user_activity_handler())


@admin_users_bp.get("/<user_id>/orders")
async def admin_user_orders_route(r: Request, user_id: str) -> HTTPResponse:
    return text(admin_user_orders_handler())


@admin_users_bp.get("/<user_id>/orders/<order_id>")
async def admin_user_order_detail_route(
    r: Request, user_id: str, order_id: str
) -> HTTPResponse:
    return text(admin_user_order_detail_handler())


admin_products_bp = Blueprint("admin_products", url_prefix="/products")
admin_products_bp.on_request(to_sanic_middleware(admin_products_permission_middleware))


@admin_products_bp.get("/")
async def admin_products_list_route(r: Request) -> HTTPResponse:
    return text(admin_products_list_handler())


@admin_products_bp.post("/")
async def admin_product_create_route(r: Request) -> HTTPResponse:
    return text(admin_product_create_handler())


@admin_products_bp.put("/<product_id>")
async def admin_product_update_route(r: Request, product_id: str) -> HTTPResponse:
    return text(admin_product_update_handler())


@admin_products_bp.delete("/<product_id>")
async def admin_product_delete_route(r: Request, product_id: str) -> HTTPResponse:
    return text(admin_product_delete_handler())


@admin_products_bp.post("/<product_id>/featured")
async def admin_product_feature_route(r: Request, product_id: str) -> HTTPResponse:
    return text(admin_product_feature_handler())


admin_orders_bp = Blueprint("admin_orders", url_prefix="/orders")
admin_orders_bp.on_request(to_sanic_middleware(admin_orders_permission_middleware))


@admin_orders_bp.get("/")
async def admin_orders_list_route(r: Request) -> HTTPResponse:
    return text(admin_orders_list_handler())


@admin_orders_bp.get("/<order_id>")
async def admin_order_detail_route(r: Request, order_id: str) -> HTTPResponse:
    return text(admin_order_detail_handler())


@admin_orders_bp.put("/<order_id>/status")
async def admin_order_status_route(r: Request, order_id: str) -> HTTPResponse:
    return text(admin_order_status_handler())


@admin_orders_bp.post("/<order_id>/refund")
async def admin_order_refund_route(r: Request, order_id: str) -> HTTPResponse:
    return text(admin_order_refund_handler())


admin_analytics_bp = Blueprint("admin_analytics", url_prefix="/analytics")


@admin_analytics_bp.get("/")
async def admin_analytics_route(r: Request) -> HTTPResponse:
    return text(admin_analytics_handler())


@admin_analytics_bp.get("/revenue")
async def admin_analytics_revenue_route(r: Request) -> HTTPResponse:
    return text(admin_analytics_revenue_handler())


@admin_analytics_bp.get("/users")
async def admin_analytics_users_route(r: Request) -> HTTPResponse:
    return text(admin_analytics_users_handler())


@admin_analytics_bp.get("/products")
async def admin_analytics_products_route(r: Request) -> HTTPResponse:
    return text(admin_analytics_products_handler())


admin_group = Blueprint.group(
    admin_users_bp,
    admin_products_bp,
    admin_orders_bp,
    admin_analytics_bp,
    url_prefix="/admin",
)

# admin base routes (need separate blueprint for routes at /admin level)
admin_bp = Blueprint("admin", url_prefix="/admin")
admin_bp.on_request(to_sanic_middleware(admin_auth_middleware))
admin_bp.on_request(to_sanic_middleware(admin_logging_middleware))


@admin_bp.get("/")
async def admin_dashboard_route(r: Request) -> HTTPResponse:
    return text(admin_dashboard_handler())


@admin_bp.get("/settings")
async def admin_settings_route(r: Request) -> HTTPResponse:
    return text(admin_settings_handler())


@admin_bp.put("/settings")
async def admin_settings_update_route(r: Request) -> HTTPResponse:
    return text(admin_settings_update_handler())


@admin_bp.get("/logs")
async def admin_logs_route(r: Request) -> HTTPResponse:
    return text(admin_logs_handler())


@admin_bp.get("/logs/<log_id>")
async def admin_log_detail_route(r: Request, log_id: str) -> HTTPResponse:
    return text(admin_log_detail_handler())


# root app
root_router = Sanic("benchmarks")
root_router.config.ACCESS_LOG = False

# root middleware
root_router.on_request(to_sanic_middleware(logging_middleware))
root_router.on_request(to_sanic_middleware(cors_middleware))


# root routes
@root_router.get("/")
async def home_route(r: Request) -> HTTPResponse:
    return text(home_handler())


@root_router.get("/about")
async def about_route(r: Request) -> HTTPResponse:
    return text(about_handler())


@root_router.get("/contact")
async def contact_route(r: Request) -> HTTPResponse:
    return text(contact_handler())


@root_router.post("/contact")
async def contact_submit_route(r: Request) -> HTTPResponse:
    return text(contact_submit_handler())


@root_router.get("/pricing")
async def pricing_route(r: Request) -> HTTPResponse:
    return text(pricing_handler())


# mount blueprints
root_router.blueprint(static_bp)
root_router.blueprint(uploads_bp)
root_router.blueprint(auth_bp)
root_router.blueprint(user_bp)
root_router.blueprint(dashboard_bp)
root_router.blueprint(products_bp)
root_router.blueprint(orders_bp)
root_router.blueprint(cart_bp)
root_router.blueprint(payments_bp)
root_router.blueprint(api_v1_bp)
root_router.blueprint(api_v1_group)
root_router.blueprint(admin_bp)
root_router.blueprint(admin_group)


# exception handlers
@root_router.exception(Exception)
async def root_exception(r: Request, e: Exception) -> HTTPResponse:
    if hasattr(e, "status_code"):
        status = e.status_code
        if status == 404:
            # check path prefix for custom handlers
            if r.path.startswith("/api/v1"):
                return text(api_not_found_handler(), status=404)
            if r.path.startswith("/admin"):
                return text(admin_not_found_handler(), status=404)
            return text(not_found_handler(), status=404)
        if status == 405:
            if r.path.startswith("/api/v1"):
                return text(api_method_not_allowed_handler(), status=405)
            if r.path.startswith("/admin"):
                return text(admin_method_not_allowed_handler(), status=405)
            return text(method_not_allowed_handler(), status=405)
    raise e
