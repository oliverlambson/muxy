"""
To run app:
    uv run granian benchmarks.app.quart:root_router --loop uvloop --interface asgi --port 8085
"""

from functools import wraps
from typing import TYPE_CHECKING

from quart import Blueprint, Quart, Response

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


def to_quart(
    h: Callable[[], str], code: int = 200
) -> Callable[[], Awaitable[Response]]:
    @wraps(h)
    async def handler(**kwargs) -> Response:
        return Response(h(), status=code, content_type="text/plain; charset=utf-8")

    return handler


def to_quart_middleware[T](m: Callable[[T], T]) -> Callable[[], Awaitable[None]]:
    @wraps(m)
    async def middleware() -> None:
        pass

    return middleware


# Static router with custom 405
static_bp = Blueprint("static", __name__, url_prefix="/static")


@static_bp.route("/<path:path>", methods=["GET"])
async def static_route(path: str) -> Response:
    return Response(
        static_handler(), status=200, content_type="text/plain; charset=utf-8"
    )


@static_bp.errorhandler(405)
async def static_405(e: Exception) -> Response:
    return Response(
        static_method_not_allowed_handler(),
        status=405,
        content_type="text/plain; charset=utf-8",
    )


# Uploads router (no middleware or custom error handlers)
uploads_bp = Blueprint("uploads", __name__, url_prefix="/uploads")


@uploads_bp.route("/<path:path>", methods=["GET"])
async def uploads_route(path: str) -> Response:
    return Response(
        uploads_handler(), status=200, content_type="text/plain; charset=utf-8"
    )


# Auth router
auth_bp = Blueprint("auth", __name__, url_prefix="/auth")
auth_bp.before_request(to_quart_middleware(auth_rate_limit_middleware))


@auth_bp.route("/login", methods=["POST"])
async def auth_login() -> Response:
    return Response(
        auth_login_handler(), status=200, content_type="text/plain; charset=utf-8"
    )


@auth_bp.route("/logout", methods=["POST"])
async def auth_logout() -> Response:
    return Response(
        auth_logout_handler(), status=200, content_type="text/plain; charset=utf-8"
    )


@auth_bp.route("/register", methods=["POST"])
async def auth_register() -> Response:
    return Response(
        auth_register_handler(), status=200, content_type="text/plain; charset=utf-8"
    )


@auth_bp.route("/password/reset", methods=["POST"])
async def auth_password_reset() -> Response:
    return Response(
        auth_password_reset_handler(),
        status=200,
        content_type="text/plain; charset=utf-8",
    )


@auth_bp.route("/password/change", methods=["POST"])
async def auth_password_change() -> Response:
    return Response(
        auth_password_change_handler(),
        status=200,
        content_type="text/plain; charset=utf-8",
    )


@auth_bp.route("/verify/<token>", methods=["GET"])
async def auth_verify(token: str) -> Response:
    return Response(
        auth_verify_handler(), status=200, content_type="text/plain; charset=utf-8"
    )


# User router
user_bp = Blueprint("user", __name__, url_prefix="/user")
user_bp.before_request(to_quart_middleware(user_auth_middleware))
user_bp.before_request(to_quart_middleware(session_middleware))


@user_bp.route("/profile", methods=["GET"])
async def user_profile() -> Response:
    return Response(
        user_profile_handler(), status=200, content_type="text/plain; charset=utf-8"
    )


@user_bp.route("/profile", methods=["PUT"])
async def user_profile_update() -> Response:
    return Response(
        user_profile_update_handler(),
        status=200,
        content_type="text/plain; charset=utf-8",
    )


@user_bp.route("/account", methods=["DELETE"])
async def user_account_delete() -> Response:
    return Response(
        user_account_delete_handler(),
        status=200,
        content_type="text/plain; charset=utf-8",
    )


@user_bp.route("/settings", methods=["GET"])
async def user_settings() -> Response:
    return Response(
        user_settings_handler(), status=200, content_type="text/plain; charset=utf-8"
    )


@user_bp.route("/settings", methods=["POST"])
async def user_settings_update() -> Response:
    return Response(
        user_settings_update_handler(),
        status=200,
        content_type="text/plain; charset=utf-8",
    )


@user_bp.route("/notifications", methods=["GET"])
async def user_notifications() -> Response:
    return Response(
        user_notifications_handler(),
        status=200,
        content_type="text/plain; charset=utf-8",
    )


@user_bp.route("/notifications/<notification_id>", methods=["PUT"])
async def user_notification_update(notification_id: str) -> Response:
    return Response(
        user_notification_update_handler(),
        status=200,
        content_type="text/plain; charset=utf-8",
    )


# Dashboard router
dashboard_bp = Blueprint("dashboard", __name__, url_prefix="/dashboard")
dashboard_bp.before_request(to_quart_middleware(user_auth_middleware))


@dashboard_bp.route("/", methods=["GET"])
async def dashboard() -> Response:
    return Response(
        dashboard_handler(), status=200, content_type="text/plain; charset=utf-8"
    )


@dashboard_bp.route("/stats", methods=["GET"])
async def dashboard_stats() -> Response:
    return Response(
        dashboard_stats_handler(), status=200, content_type="text/plain; charset=utf-8"
    )


@dashboard_bp.route("/activity", methods=["GET"])
async def dashboard_activity() -> Response:
    return Response(
        dashboard_activity_handler(),
        status=200,
        content_type="text/plain; charset=utf-8",
    )


# Products router
products_bp = Blueprint("products", __name__, url_prefix="/products")
products_bp.before_request(to_quart_middleware(cache_middleware))


@products_bp.route("/", methods=["GET"])
async def products_list() -> Response:
    return Response(
        products_list_handler(), status=200, content_type="text/plain; charset=utf-8"
    )


@products_bp.route("/<product_id>", methods=["GET"])
async def product_detail(product_id: str) -> Response:
    return Response(
        product_detail_handler(), status=200, content_type="text/plain; charset=utf-8"
    )


@products_bp.route("/", methods=["POST"])
async def product_create() -> Response:
    return Response(
        product_create_handler(), status=200, content_type="text/plain; charset=utf-8"
    )


@products_bp.route("/<product_id>", methods=["PUT"])
async def product_update(product_id: str) -> Response:
    return Response(
        product_update_handler(), status=200, content_type="text/plain; charset=utf-8"
    )


@products_bp.route("/<product_id>", methods=["DELETE"])
async def product_delete(product_id: str) -> Response:
    return Response(
        product_delete_handler(), status=200, content_type="text/plain; charset=utf-8"
    )


@products_bp.route("/<product_id>/reviews", methods=["GET"])
async def product_reviews(product_id: str) -> Response:
    return Response(
        product_reviews_handler(), status=200, content_type="text/plain; charset=utf-8"
    )


@products_bp.route("/<product_id>/reviews", methods=["POST"])
async def product_review_create(product_id: str) -> Response:
    return Response(
        product_review_create_handler(),
        status=200,
        content_type="text/plain; charset=utf-8",
    )


# Orders router
orders_bp = Blueprint("orders", __name__, url_prefix="/orders")
orders_bp.before_request(to_quart_middleware(user_auth_middleware))


@orders_bp.route("/", methods=["GET"])
async def orders_list() -> Response:
    return Response(
        orders_list_handler(), status=200, content_type="text/plain; charset=utf-8"
    )


@orders_bp.route("/<order_id>", methods=["GET"])
async def order_detail(order_id: str) -> Response:
    return Response(
        order_detail_handler(), status=200, content_type="text/plain; charset=utf-8"
    )


@orders_bp.route("/", methods=["POST"])
async def order_create() -> Response:
    return Response(
        order_create_handler(), status=200, content_type="text/plain; charset=utf-8"
    )


@orders_bp.route("/<order_id>/cancel", methods=["PUT"])
async def order_cancel(order_id: str) -> Response:
    return Response(
        order_cancel_handler(), status=200, content_type="text/plain; charset=utf-8"
    )


@orders_bp.route("/<order_id>/invoice", methods=["GET"])
async def order_invoice(order_id: str) -> Response:
    return Response(
        order_invoice_handler(), status=200, content_type="text/plain; charset=utf-8"
    )


# Cart router
cart_bp = Blueprint("cart", __name__, url_prefix="/cart")
cart_bp.before_request(to_quart_middleware(session_middleware))


@cart_bp.route("/", methods=["GET"])
async def cart_view() -> Response:
    return Response(
        cart_view_handler(), status=200, content_type="text/plain; charset=utf-8"
    )


@cart_bp.route("/items", methods=["POST"])
async def cart_add_item() -> Response:
    return Response(
        cart_add_item_handler(), status=200, content_type="text/plain; charset=utf-8"
    )


@cart_bp.route("/items/<item_id>", methods=["PUT"])
async def cart_update_item(item_id: str) -> Response:
    return Response(
        cart_update_item_handler(), status=200, content_type="text/plain; charset=utf-8"
    )


@cart_bp.route("/items/<item_id>", methods=["DELETE"])
async def cart_remove_item(item_id: str) -> Response:
    return Response(
        cart_remove_item_handler(), status=200, content_type="text/plain; charset=utf-8"
    )


@cart_bp.route("/checkout", methods=["POST"])
async def cart_checkout() -> Response:
    return Response(
        cart_checkout_handler(), status=200, content_type="text/plain; charset=utf-8"
    )


# Payments router
payments_bp = Blueprint("payments", __name__, url_prefix="/payments")
payments_bp.before_request(to_quart_middleware(user_auth_middleware))
payments_bp.before_request(to_quart_middleware(payment_security_middleware))


@payments_bp.route("/process", methods=["POST"])
async def payment_process() -> Response:
    return Response(
        payment_process_handler(), status=200, content_type="text/plain; charset=utf-8"
    )


@payments_bp.route("/<payment_id>/status", methods=["GET"])
async def payment_status(payment_id: str) -> Response:
    return Response(
        payment_status_handler(), status=200, content_type="text/plain; charset=utf-8"
    )


@payments_bp.route("/<payment_id>/refund", methods=["POST"])
async def payment_refund(payment_id: str) -> Response:
    return Response(
        payment_refund_handler(), status=200, content_type="text/plain; charset=utf-8"
    )


# API v1 nested routers
api_products_bp = Blueprint("api_products", __name__, url_prefix="/products")


@api_products_bp.route("/", methods=["GET"])
async def api_products() -> Response:
    return Response(
        api_products_handler(), status=200, content_type="text/plain; charset=utf-8"
    )


@api_products_bp.route("/<product_id>", methods=["GET"])
async def api_product(product_id: str) -> Response:
    return Response(
        api_product_handler(), status=200, content_type="text/plain; charset=utf-8"
    )


@api_products_bp.route("/<product_id>/reviews", methods=["POST"])
async def api_product_review(product_id: str) -> Response:
    return Response(
        api_product_review_handler(),
        status=200,
        content_type="text/plain; charset=utf-8",
    )


@api_products_bp.route("/<product_id>/reviews/<review_id>", methods=["GET"])
async def api_product_review_detail(product_id: str, review_id: str) -> Response:
    return Response(
        api_product_review_detail_handler(),
        status=200,
        content_type="text/plain; charset=utf-8",
    )


api_orders_bp = Blueprint("api_orders", __name__, url_prefix="/orders")


@api_orders_bp.route("/", methods=["GET"])
async def api_orders() -> Response:
    return Response(
        api_orders_handler(), status=200, content_type="text/plain; charset=utf-8"
    )


@api_orders_bp.route("/<order_id>", methods=["GET"])
async def api_order(order_id: str) -> Response:
    return Response(
        api_order_handler(), status=200, content_type="text/plain; charset=utf-8"
    )


api_user_bp = Blueprint("api_user", __name__, url_prefix="/user")


@api_user_bp.route("/profile", methods=["GET"])
async def api_user_profile() -> Response:
    return Response(
        api_user_profile_handler(), status=200, content_type="text/plain; charset=utf-8"
    )


# API v1 router
api_v1_bp = Blueprint("api_v1", __name__, url_prefix="/api/v1")
api_v1_bp.before_request(to_quart_middleware(rate_limit_middleware))
api_v1_bp.before_request(to_quart_middleware(api_auth_middleware))


@api_v1_bp.route("/health", methods=["GET"])
async def api_health() -> Response:
    return Response(
        api_health_handler(), status=200, content_type="text/plain; charset=utf-8"
    )


@api_v1_bp.route("/status", methods=["GET"])
async def api_status() -> Response:
    return Response(
        api_status_handler(), status=200, content_type="text/plain; charset=utf-8"
    )


@api_v1_bp.errorhandler(404)
async def api_404(e: Exception) -> Response:
    return Response(
        api_not_found_handler(), status=404, content_type="text/plain; charset=utf-8"
    )


@api_v1_bp.errorhandler(405)
async def api_405(e: Exception) -> Response:
    return Response(
        api_method_not_allowed_handler(),
        status=405,
        content_type="text/plain; charset=utf-8",
    )


api_v1_bp.register_blueprint(api_products_bp)
api_v1_bp.register_blueprint(api_orders_bp)
api_v1_bp.register_blueprint(api_user_bp)


# Admin nested routers
admin_users_bp = Blueprint("admin_users", __name__, url_prefix="/users")
admin_users_bp.before_request(to_quart_middleware(admin_users_permission_middleware))


@admin_users_bp.route("/", methods=["GET"])
async def admin_users_list() -> Response:
    return Response(
        admin_users_list_handler(), status=200, content_type="text/plain; charset=utf-8"
    )


@admin_users_bp.route("/<user_id>", methods=["GET"])
async def admin_user_detail(user_id: str) -> Response:
    return Response(
        admin_user_detail_handler(),
        status=200,
        content_type="text/plain; charset=utf-8",
    )


@admin_users_bp.route("/<user_id>", methods=["PUT"])
async def admin_user_update(user_id: str) -> Response:
    return Response(
        admin_user_update_handler(),
        status=200,
        content_type="text/plain; charset=utf-8",
    )


@admin_users_bp.route("/<user_id>", methods=["DELETE"])
async def admin_user_delete(user_id: str) -> Response:
    return Response(
        admin_user_delete_handler(),
        status=200,
        content_type="text/plain; charset=utf-8",
    )


@admin_users_bp.route("/<user_id>/suspend", methods=["POST"])
async def admin_user_suspend(user_id: str) -> Response:
    return Response(
        admin_user_suspend_handler(),
        status=200,
        content_type="text/plain; charset=utf-8",
    )


@admin_users_bp.route("/<user_id>/activate", methods=["POST"])
async def admin_user_activate(user_id: str) -> Response:
    return Response(
        admin_user_activate_handler(),
        status=200,
        content_type="text/plain; charset=utf-8",
    )


@admin_users_bp.route("/<user_id>/activity", methods=["GET"])
async def admin_user_activity(user_id: str) -> Response:
    return Response(
        admin_user_activity_handler(),
        status=200,
        content_type="text/plain; charset=utf-8",
    )


@admin_users_bp.route("/<user_id>/orders", methods=["GET"])
async def admin_user_orders(user_id: str) -> Response:
    return Response(
        admin_user_orders_handler(),
        status=200,
        content_type="text/plain; charset=utf-8",
    )


@admin_users_bp.route("/<user_id>/orders/<order_id>", methods=["GET"])
async def admin_user_order_detail(user_id: str, order_id: str) -> Response:
    return Response(
        admin_user_order_detail_handler(),
        status=200,
        content_type="text/plain; charset=utf-8",
    )


admin_products_bp = Blueprint("admin_products", __name__, url_prefix="/products")
admin_products_bp.before_request(
    to_quart_middleware(admin_products_permission_middleware)
)


@admin_products_bp.route("/", methods=["GET"])
async def admin_products_list() -> Response:
    return Response(
        admin_products_list_handler(),
        status=200,
        content_type="text/plain; charset=utf-8",
    )


@admin_products_bp.route("/", methods=["POST"])
async def admin_product_create() -> Response:
    return Response(
        admin_product_create_handler(),
        status=200,
        content_type="text/plain; charset=utf-8",
    )


@admin_products_bp.route("/<product_id>", methods=["PUT"])
async def admin_product_update(product_id: str) -> Response:
    return Response(
        admin_product_update_handler(),
        status=200,
        content_type="text/plain; charset=utf-8",
    )


@admin_products_bp.route("/<product_id>", methods=["DELETE"])
async def admin_product_delete(product_id: str) -> Response:
    return Response(
        admin_product_delete_handler(),
        status=200,
        content_type="text/plain; charset=utf-8",
    )


@admin_products_bp.route("/<product_id>/featured", methods=["POST"])
async def admin_product_feature(product_id: str) -> Response:
    return Response(
        admin_product_feature_handler(),
        status=200,
        content_type="text/plain; charset=utf-8",
    )


admin_orders_bp = Blueprint("admin_orders", __name__, url_prefix="/orders")
admin_orders_bp.before_request(to_quart_middleware(admin_orders_permission_middleware))


@admin_orders_bp.route("/", methods=["GET"])
async def admin_orders_list() -> Response:
    return Response(
        admin_orders_list_handler(),
        status=200,
        content_type="text/plain; charset=utf-8",
    )


@admin_orders_bp.route("/<order_id>", methods=["GET"])
async def admin_order_detail(order_id: str) -> Response:
    return Response(
        admin_order_detail_handler(),
        status=200,
        content_type="text/plain; charset=utf-8",
    )


@admin_orders_bp.route("/<order_id>/status", methods=["PUT"])
async def admin_order_status(order_id: str) -> Response:
    return Response(
        admin_order_status_handler(),
        status=200,
        content_type="text/plain; charset=utf-8",
    )


@admin_orders_bp.route("/<order_id>/refund", methods=["POST"])
async def admin_order_refund(order_id: str) -> Response:
    return Response(
        admin_order_refund_handler(),
        status=200,
        content_type="text/plain; charset=utf-8",
    )


admin_analytics_bp = Blueprint("admin_analytics", __name__, url_prefix="/analytics")


@admin_analytics_bp.route("/", methods=["GET"])
async def admin_analytics() -> Response:
    return Response(
        admin_analytics_handler(), status=200, content_type="text/plain; charset=utf-8"
    )


@admin_analytics_bp.route("/revenue", methods=["GET"])
async def admin_analytics_revenue() -> Response:
    return Response(
        admin_analytics_revenue_handler(),
        status=200,
        content_type="text/plain; charset=utf-8",
    )


@admin_analytics_bp.route("/users", methods=["GET"])
async def admin_analytics_users() -> Response:
    return Response(
        admin_analytics_users_handler(),
        status=200,
        content_type="text/plain; charset=utf-8",
    )


@admin_analytics_bp.route("/products", methods=["GET"])
async def admin_analytics_products() -> Response:
    return Response(
        admin_analytics_products_handler(),
        status=200,
        content_type="text/plain; charset=utf-8",
    )


# Admin router
admin_bp = Blueprint("admin", __name__, url_prefix="/admin")
admin_bp.before_request(to_quart_middleware(admin_auth_middleware))
admin_bp.before_request(to_quart_middleware(admin_logging_middleware))


@admin_bp.route("/", methods=["GET"])
async def admin_dashboard() -> Response:
    return Response(
        admin_dashboard_handler(), status=200, content_type="text/plain; charset=utf-8"
    )


@admin_bp.route("/settings", methods=["GET"])
async def admin_settings() -> Response:
    return Response(
        admin_settings_handler(), status=200, content_type="text/plain; charset=utf-8"
    )


@admin_bp.route("/settings", methods=["PUT"])
async def admin_settings_update() -> Response:
    return Response(
        admin_settings_update_handler(),
        status=200,
        content_type="text/plain; charset=utf-8",
    )


@admin_bp.route("/logs", methods=["GET"])
async def admin_logs() -> Response:
    return Response(
        admin_logs_handler(), status=200, content_type="text/plain; charset=utf-8"
    )


@admin_bp.route("/logs/<log_id>", methods=["GET"])
async def admin_log_detail(log_id: str) -> Response:
    return Response(
        admin_log_detail_handler(), status=200, content_type="text/plain; charset=utf-8"
    )


@admin_bp.errorhandler(404)
async def admin_404(e: Exception) -> Response:
    return Response(
        admin_not_found_handler(), status=404, content_type="text/plain; charset=utf-8"
    )


@admin_bp.errorhandler(405)
async def admin_405(e: Exception) -> Response:
    return Response(
        admin_method_not_allowed_handler(),
        status=405,
        content_type="text/plain; charset=utf-8",
    )


admin_bp.register_blueprint(admin_users_bp)
admin_bp.register_blueprint(admin_products_bp)
admin_bp.register_blueprint(admin_orders_bp)
admin_bp.register_blueprint(admin_analytics_bp)


# Root router
root_router = Quart(__name__)


@root_router.before_request
async def root_logging() -> None:
    logging_middleware(None)


@root_router.before_request
async def root_cors() -> None:
    cors_middleware(None)


@root_router.route("/", methods=["GET"])
async def home() -> Response:
    return Response(
        home_handler(), status=200, content_type="text/plain; charset=utf-8"
    )


@root_router.route("/about", methods=["GET"])
async def about() -> Response:
    return Response(
        about_handler(), status=200, content_type="text/plain; charset=utf-8"
    )


@root_router.route("/contact", methods=["GET"])
async def contact() -> Response:
    return Response(
        contact_handler(), status=200, content_type="text/plain; charset=utf-8"
    )


@root_router.route("/contact", methods=["POST"])
async def contact_submit() -> Response:
    return Response(
        contact_submit_handler(), status=200, content_type="text/plain; charset=utf-8"
    )


@root_router.route("/pricing", methods=["GET"])
async def pricing() -> Response:
    return Response(
        pricing_handler(), status=200, content_type="text/plain; charset=utf-8"
    )


@root_router.errorhandler(404)
async def root_404(e: Exception) -> Response:
    return Response(
        not_found_handler(), status=404, content_type="text/plain; charset=utf-8"
    )


@root_router.errorhandler(405)
async def root_405(e: Exception) -> Response:
    return Response(
        method_not_allowed_handler(),
        status=405,
        content_type="text/plain; charset=utf-8",
    )


# Register all blueprints
root_router.register_blueprint(static_bp)
root_router.register_blueprint(uploads_bp)
root_router.register_blueprint(auth_bp)
root_router.register_blueprint(user_bp)
root_router.register_blueprint(dashboard_bp)
root_router.register_blueprint(products_bp)
root_router.register_blueprint(orders_bp)
root_router.register_blueprint(cart_bp)
root_router.register_blueprint(payments_bp)
root_router.register_blueprint(api_v1_bp)
root_router.register_blueprint(admin_bp)
