"""
To run app:
    uv run granian benchmarks.app.emmett55:root_router --loop uvloop --interface rsgi --port 8087
"""

from emmett55 import App, AppModule, Pipe, response

from ._common import (
    about_handler,
    admin_analytics_handler,
    admin_analytics_products_handler,
    admin_analytics_revenue_handler,
    admin_analytics_users_handler,
    admin_dashboard_handler,
    admin_log_detail_handler,
    admin_logs_handler,
    admin_order_detail_handler,
    admin_order_refund_handler,
    admin_order_status_handler,
    admin_orders_list_handler,
    admin_product_create_handler,
    admin_product_delete_handler,
    admin_product_feature_handler,
    admin_product_update_handler,
    admin_products_list_handler,
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
    api_health_handler,
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
    auth_register_handler,
    auth_verify_handler,
    cart_add_item_handler,
    cart_checkout_handler,
    cart_remove_item_handler,
    cart_update_item_handler,
    cart_view_handler,
    contact_handler,
    contact_submit_handler,
    dashboard_activity_handler,
    dashboard_handler,
    dashboard_stats_handler,
    home_handler,
    order_cancel_handler,
    order_create_handler,
    order_detail_handler,
    order_invoice_handler,
    orders_list_handler,
    payment_process_handler,
    payment_refund_handler,
    payment_status_handler,
    pricing_handler,
    product_create_handler,
    product_delete_handler,
    product_detail_handler,
    product_review_create_handler,
    product_reviews_handler,
    product_update_handler,
    products_list_handler,
    static_handler,
    uploads_handler,
    user_account_delete_handler,
    user_notification_update_handler,
    user_notifications_handler,
    user_profile_handler,
    user_profile_update_handler,
    user_settings_handler,
    user_settings_update_handler,
)


# No-op Pipe classes for middleware simulation
# These match the middleware structure in other benchmark frameworks
class LoggingPipe(Pipe):
    async def pipe(self, next_pipe, **kwargs):
        return await next_pipe(**kwargs)


class CorsPipe(Pipe):
    async def pipe(self, next_pipe, **kwargs):
        return await next_pipe(**kwargs)


class AuthRateLimitPipe(Pipe):
    async def pipe(self, next_pipe, **kwargs):
        return await next_pipe(**kwargs)


class UserAuthPipe(Pipe):
    async def pipe(self, next_pipe, **kwargs):
        return await next_pipe(**kwargs)


class SessionPipe(Pipe):
    async def pipe(self, next_pipe, **kwargs):
        return await next_pipe(**kwargs)


class CachePipe(Pipe):
    async def pipe(self, next_pipe, **kwargs):
        return await next_pipe(**kwargs)


class PaymentSecurityPipe(Pipe):
    async def pipe(self, next_pipe, **kwargs):
        return await next_pipe(**kwargs)


class RateLimitPipe(Pipe):
    async def pipe(self, next_pipe, **kwargs):
        return await next_pipe(**kwargs)


class ApiAuthPipe(Pipe):
    async def pipe(self, next_pipe, **kwargs):
        return await next_pipe(**kwargs)


class AdminAuthPipe(Pipe):
    async def pipe(self, next_pipe, **kwargs):
        return await next_pipe(**kwargs)


class AdminLoggingPipe(Pipe):
    async def pipe(self, next_pipe, **kwargs):
        return await next_pipe(**kwargs)


class AdminUsersPermissionPipe(Pipe):
    async def pipe(self, next_pipe, **kwargs):
        return await next_pipe(**kwargs)


class AdminProductsPermissionPipe(Pipe):
    async def pipe(self, next_pipe, **kwargs):
        return await next_pipe(**kwargs)


class AdminOrdersPermissionPipe(Pipe):
    async def pipe(self, next_pipe, **kwargs):
        return await next_pipe(**kwargs)


# Create main app
app = App(__name__)
app.pipeline = [LoggingPipe(), CorsPipe()]


# Static routes (defined on app due to /static potentially being reserved)
@app.route("/static/<str:path>", methods="get")
async def static_files_route(path):
    response.content_type = "text/plain"
    return static_handler()


# Uploads routes
@app.route("/uploads/<str:path>", methods="get")
async def uploads_route(path):
    response.content_type = "text/plain"
    return uploads_handler()


# Auth module
auth_mod = AppModule(app, "auth", __name__, url_prefix="/auth")
auth_mod.pipeline = [AuthRateLimitPipe()]


@auth_mod.route("/login", methods="post")
async def auth_login_route():
    response.content_type = "text/plain"
    return auth_login_handler()


@auth_mod.route("/logout", methods="post")
async def auth_logout_route():
    response.content_type = "text/plain"
    return auth_logout_handler()


@auth_mod.route("/register", methods="post")
async def auth_register_route():
    response.content_type = "text/plain"
    return auth_register_handler()


@auth_mod.route("/password/reset", methods="post")
async def auth_password_reset_route():
    response.content_type = "text/plain"
    return auth_password_reset_handler()


@auth_mod.route("/password/change", methods="post")
async def auth_password_change_route():
    response.content_type = "text/plain"
    return auth_password_change_handler()


@auth_mod.route("/verify/<str:token>", methods="get")
async def auth_verify_route(token):
    response.content_type = "text/plain"
    return auth_verify_handler()


# User module
user_mod = AppModule(app, "user", __name__, url_prefix="/user")
user_mod.pipeline = [UserAuthPipe(), SessionPipe()]


@user_mod.route("/profile", methods="get")
async def user_profile_route():
    response.content_type = "text/plain"
    return user_profile_handler()


@user_mod.route("/profile", methods="put")
async def user_profile_update_route():
    response.content_type = "text/plain"
    return user_profile_update_handler()


@user_mod.route("/account", methods="delete")
async def user_account_delete_route():
    response.content_type = "text/plain"
    return user_account_delete_handler()


@user_mod.route("/settings", methods="get")
async def user_settings_route():
    response.content_type = "text/plain"
    return user_settings_handler()


@user_mod.route("/settings", methods="post")
async def user_settings_update_route():
    response.content_type = "text/plain"
    return user_settings_update_handler()


@user_mod.route("/notifications", methods="get")
async def user_notifications_route():
    response.content_type = "text/plain"
    return user_notifications_handler()


@user_mod.route("/notifications/<int:notification_id>", methods="put")
async def user_notification_update_route(notification_id):
    response.content_type = "text/plain"
    return user_notification_update_handler()


# Dashboard module
dashboard_mod = AppModule(app, "dashboard", __name__, url_prefix="/dashboard")
dashboard_mod.pipeline = [UserAuthPipe()]


@dashboard_mod.route("/", methods="get")
async def dashboard_route():
    response.content_type = "text/plain"
    return dashboard_handler()


@dashboard_mod.route("/stats", methods="get")
async def dashboard_stats_route():
    response.content_type = "text/plain"
    return dashboard_stats_handler()


@dashboard_mod.route("/activity", methods="get")
async def dashboard_activity_route():
    response.content_type = "text/plain"
    return dashboard_activity_handler()


# Products module
products_mod = AppModule(app, "products", __name__, url_prefix="/products")
products_mod.pipeline = [CachePipe()]


@products_mod.route("/", methods="get")
async def products_list_route():
    response.content_type = "text/plain"
    return products_list_handler()


@products_mod.route("/<int:product_id>", methods="get")
async def product_detail_route(product_id):
    response.content_type = "text/plain"
    return product_detail_handler()


@products_mod.route("/", methods="post")
async def product_create_route():
    response.content_type = "text/plain"
    return product_create_handler()


@products_mod.route("/<int:product_id>", methods="put")
async def product_update_route(product_id):
    response.content_type = "text/plain"
    return product_update_handler()


@products_mod.route("/<int:product_id>", methods="delete")
async def product_delete_route(product_id):
    response.content_type = "text/plain"
    return product_delete_handler()


@products_mod.route("/<int:product_id>/reviews", methods="get")
async def product_reviews_route(product_id):
    response.content_type = "text/plain"
    return product_reviews_handler()


@products_mod.route("/<int:product_id>/reviews", methods="post")
async def product_review_create_route(product_id):
    response.content_type = "text/plain"
    return product_review_create_handler()


# Orders module
orders_mod = AppModule(app, "orders", __name__, url_prefix="/orders")
orders_mod.pipeline = [UserAuthPipe()]


@orders_mod.route("/", methods="get")
async def orders_list_route():
    response.content_type = "text/plain"
    return orders_list_handler()


@orders_mod.route("/<int:order_id>", methods="get")
async def order_detail_route(order_id):
    response.content_type = "text/plain"
    return order_detail_handler()


@orders_mod.route("/", methods="post")
async def order_create_route():
    response.content_type = "text/plain"
    return order_create_handler()


@orders_mod.route("/<int:order_id>/cancel", methods="put")
async def order_cancel_route(order_id):
    response.content_type = "text/plain"
    return order_cancel_handler()


@orders_mod.route("/<int:order_id>/invoice", methods="get")
async def order_invoice_route(order_id):
    response.content_type = "text/plain"
    return order_invoice_handler()


# Cart module
cart_mod = AppModule(app, "cart", __name__, url_prefix="/cart")
cart_mod.pipeline = [SessionPipe()]


@cart_mod.route("/", methods="get")
async def cart_view_route():
    response.content_type = "text/plain"
    return cart_view_handler()


@cart_mod.route("/items", methods="post")
async def cart_add_item_route():
    response.content_type = "text/plain"
    return cart_add_item_handler()


@cart_mod.route("/items/<int:item_id>", methods="put")
async def cart_update_item_route(item_id):
    response.content_type = "text/plain"
    return cart_update_item_handler()


@cart_mod.route("/items/<int:item_id>", methods="delete")
async def cart_remove_item_route(item_id):
    response.content_type = "text/plain"
    return cart_remove_item_handler()


@cart_mod.route("/checkout", methods="post")
async def cart_checkout_route():
    response.content_type = "text/plain"
    return cart_checkout_handler()


# Payments module
payments_mod = AppModule(app, "payments", __name__, url_prefix="/payments")
payments_mod.pipeline = [UserAuthPipe(), PaymentSecurityPipe()]


@payments_mod.route("/process", methods="post")
async def payment_process_route():
    response.content_type = "text/plain"
    return payment_process_handler()


@payments_mod.route("/<int:payment_id>/status", methods="get")
async def payment_status_route(payment_id):
    response.content_type = "text/plain"
    return payment_status_handler()


@payments_mod.route("/<int:payment_id>/refund", methods="post")
async def payment_refund_route(payment_id):
    response.content_type = "text/plain"
    return payment_refund_handler()


# API v1 module
api_v1_mod = AppModule(app, "api_v1", __name__, url_prefix="/api/v1")
api_v1_mod.pipeline = [RateLimitPipe(), ApiAuthPipe()]


@api_v1_mod.route("/health", methods="get")
async def api_health_route():
    response.content_type = "text/plain"
    return api_health_handler()


@api_v1_mod.route("/status", methods="get")
async def api_status_route():
    response.content_type = "text/plain"
    return api_status_handler()


# API products (nested under api_v1)
@api_v1_mod.route("/products", methods="get")
async def api_products_route():
    response.content_type = "text/plain"
    return api_products_handler()


@api_v1_mod.route("/products/<int:product_id>", methods="get")
async def api_product_route(product_id):
    response.content_type = "text/plain"
    return api_product_handler()


@api_v1_mod.route("/products/<int:product_id>/reviews", methods="post")
async def api_product_review_route(product_id):
    response.content_type = "text/plain"
    return api_product_review_handler()


@api_v1_mod.route("/products/<int:product_id>/reviews/<int:review_id>", methods="get")
async def api_product_review_detail_route(product_id, review_id):
    response.content_type = "text/plain"
    return api_product_review_detail_handler()


# API orders (nested under api_v1)
@api_v1_mod.route("/orders", methods="get")
async def api_orders_route():
    response.content_type = "text/plain"
    return api_orders_handler()


@api_v1_mod.route("/orders/<int:order_id>", methods="get")
async def api_order_route(order_id):
    response.content_type = "text/plain"
    return api_order_handler()


# API user (nested under api_v1)
@api_v1_mod.route("/user/profile", methods="get")
async def api_user_profile_route():
    response.content_type = "text/plain"
    return api_user_profile_handler()


# Admin module
admin_mod = AppModule(app, "admin", __name__, url_prefix="/admin")
admin_mod.pipeline = [AdminAuthPipe(), AdminLoggingPipe()]


@admin_mod.route("/", methods="get")
async def admin_dashboard_route():
    response.content_type = "text/plain"
    return admin_dashboard_handler()


@admin_mod.route("/settings", methods="get")
async def admin_settings_route():
    response.content_type = "text/plain"
    return admin_settings_handler()


@admin_mod.route("/settings", methods="put")
async def admin_settings_update_route():
    response.content_type = "text/plain"
    return admin_settings_update_handler()


@admin_mod.route("/logs", methods="get")
async def admin_logs_route():
    response.content_type = "text/plain"
    return admin_logs_handler()


@admin_mod.route("/logs/<int:log_id>", methods="get")
async def admin_log_detail_route(log_id):
    response.content_type = "text/plain"
    return admin_log_detail_handler()


# Admin users submodule
admin_users_mod = AppModule(app, "admin_users", __name__, url_prefix="/admin/users")
admin_users_mod.pipeline = [
    AdminAuthPipe(),
    AdminLoggingPipe(),
    AdminUsersPermissionPipe(),
]


@admin_users_mod.route("/", methods="get")
async def admin_users_list_route():
    response.content_type = "text/plain"
    return admin_users_list_handler()


@admin_users_mod.route("/<int:user_id>", methods="get")
async def admin_user_detail_route(user_id):
    response.content_type = "text/plain"
    return admin_user_detail_handler()


@admin_users_mod.route("/<int:user_id>", methods="put")
async def admin_user_update_route(user_id):
    response.content_type = "text/plain"
    return admin_user_update_handler()


@admin_users_mod.route("/<int:user_id>", methods="delete")
async def admin_user_delete_route(user_id):
    response.content_type = "text/plain"
    return admin_user_delete_handler()


@admin_users_mod.route("/<int:user_id>/suspend", methods="post")
async def admin_user_suspend_route(user_id):
    response.content_type = "text/plain"
    return admin_user_suspend_handler()


@admin_users_mod.route("/<int:user_id>/activate", methods="post")
async def admin_user_activate_route(user_id):
    response.content_type = "text/plain"
    return admin_user_activate_handler()


@admin_users_mod.route("/<int:user_id>/activity", methods="get")
async def admin_user_activity_route(user_id):
    response.content_type = "text/plain"
    return admin_user_activity_handler()


@admin_users_mod.route("/<int:user_id>/orders", methods="get")
async def admin_user_orders_route(user_id):
    response.content_type = "text/plain"
    return admin_user_orders_handler()


@admin_users_mod.route("/<int:user_id>/orders/<int:order_id>", methods="get")
async def admin_user_order_detail_route(user_id, order_id):
    response.content_type = "text/plain"
    return admin_user_order_detail_handler()


# Admin products submodule
admin_products_mod = AppModule(
    app, "admin_products", __name__, url_prefix="/admin/products"
)
admin_products_mod.pipeline = [
    AdminAuthPipe(),
    AdminLoggingPipe(),
    AdminProductsPermissionPipe(),
]


@admin_products_mod.route("/", methods="get")
async def admin_products_list_route():
    response.content_type = "text/plain"
    return admin_products_list_handler()


@admin_products_mod.route("/", methods="post")
async def admin_product_create_route():
    response.content_type = "text/plain"
    return admin_product_create_handler()


@admin_products_mod.route("/<int:product_id>", methods="put")
async def admin_product_update_route(product_id):
    response.content_type = "text/plain"
    return admin_product_update_handler()


@admin_products_mod.route("/<int:product_id>", methods="delete")
async def admin_product_delete_route(product_id):
    response.content_type = "text/plain"
    return admin_product_delete_handler()


@admin_products_mod.route("/<int:product_id>/featured", methods="post")
async def admin_product_feature_route(product_id):
    response.content_type = "text/plain"
    return admin_product_feature_handler()


# Admin orders submodule
admin_orders_mod = AppModule(app, "admin_orders", __name__, url_prefix="/admin/orders")
admin_orders_mod.pipeline = [
    AdminAuthPipe(),
    AdminLoggingPipe(),
    AdminOrdersPermissionPipe(),
]


@admin_orders_mod.route("/", methods="get")
async def admin_orders_list_route():
    response.content_type = "text/plain"
    return admin_orders_list_handler()


@admin_orders_mod.route("/<int:order_id>", methods="get")
async def admin_order_detail_route(order_id):
    response.content_type = "text/plain"
    return admin_order_detail_handler()


@admin_orders_mod.route("/<int:order_id>/status", methods="put")
async def admin_order_status_route(order_id):
    response.content_type = "text/plain"
    return admin_order_status_handler()


@admin_orders_mod.route("/<int:order_id>/refund", methods="post")
async def admin_order_refund_route(order_id):
    response.content_type = "text/plain"
    return admin_order_refund_handler()


# Admin analytics submodule
admin_analytics_mod = AppModule(
    app, "admin_analytics", __name__, url_prefix="/admin/analytics"
)
admin_analytics_mod.pipeline = [AdminAuthPipe(), AdminLoggingPipe()]


@admin_analytics_mod.route("/", methods="get")
async def admin_analytics_route():
    response.content_type = "text/plain"
    return admin_analytics_handler()


@admin_analytics_mod.route("/revenue", methods="get")
async def admin_analytics_revenue_route():
    response.content_type = "text/plain"
    return admin_analytics_revenue_handler()


@admin_analytics_mod.route("/users", methods="get")
async def admin_analytics_users_route():
    response.content_type = "text/plain"
    return admin_analytics_users_handler()


@admin_analytics_mod.route("/products", methods="get")
async def admin_analytics_products_route():
    response.content_type = "text/plain"
    return admin_analytics_products_handler()


# Root-level routes
@app.route("/", methods="get")
async def home_route():
    response.content_type = "text/plain"
    return home_handler()


@app.route("/about", methods="get")
async def about_route():
    response.content_type = "text/plain"
    return about_handler()


@app.route("/contact", methods="get")
async def contact_route():
    response.content_type = "text/plain"
    return contact_handler()


@app.route("/contact", methods="post")
async def contact_submit_route():
    response.content_type = "text/plain"
    return contact_submit_handler()


@app.route("/pricing", methods="get")
async def pricing_route():
    response.content_type = "text/plain"
    return pricing_handler()


# Export the app as root_router for granian
root_router = app
