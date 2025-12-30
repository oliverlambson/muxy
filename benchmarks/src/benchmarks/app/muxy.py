"""
To run app:
    uv run granian benchmarks.app.muxy:root_router --loop uvloop --interface rsgi --port 8080
"""

from collections.abc import Callable
from functools import wraps

from muxy import Router
from muxy.rsgi import HTTPProtocol, HTTPScope, RSGIHTTPHandler

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


def to_rsgi(h: Callable[[], str], code: int = 200) -> RSGIHTTPHandler:
    @wraps(h)
    async def handler(s: HTTPScope, p: HTTPProtocol) -> None:
        p.response_str(code, [("Content-Type", "text/plain")], h())

    return handler


static_router = Router()
static_router.method_not_allowed(to_rsgi(static_method_not_allowed_handler, 405))
static_router.get("/{path...}", to_rsgi(static_handler))

uploads_router = Router()
uploads_router.get("/{path...}", to_rsgi(uploads_handler))

auth_router = Router()
auth_router.use(auth_rate_limit_middleware)
auth_router.post("/login", to_rsgi(auth_login_handler))
auth_router.post("/logout", to_rsgi(auth_logout_handler))
auth_router.post("/register", to_rsgi(auth_register_handler))
auth_router.post("/password/reset", to_rsgi(auth_password_reset_handler))
auth_router.post("/password/change", to_rsgi(auth_password_change_handler))
auth_router.get("/verify/{token}", to_rsgi(auth_verify_handler))

user_router = Router()
user_router.use(user_auth_middleware, session_middleware)
user_router.get("/profile", to_rsgi(user_profile_handler))
user_router.put("/profile", to_rsgi(user_profile_update_handler))
user_router.delete("/account", to_rsgi(user_account_delete_handler))
user_router.get("/settings", to_rsgi(user_settings_handler))
user_router.post("/settings", to_rsgi(user_settings_update_handler))
user_router.get("/notifications", to_rsgi(user_notifications_handler))
user_router.put(
    "/notifications/{notification_id}", to_rsgi(user_notification_update_handler)
)

dashboard_router = Router()
dashboard_router.use(user_auth_middleware)
dashboard_router.get("/", to_rsgi(dashboard_handler))
dashboard_router.get("/stats", to_rsgi(dashboard_stats_handler))
dashboard_router.get("/activity", to_rsgi(dashboard_activity_handler))

products_router = Router()
products_router.use(cache_middleware)
products_router.get("/", to_rsgi(products_list_handler))
products_router.get("/{product_id}", to_rsgi(product_detail_handler))
products_router.post("/", to_rsgi(product_create_handler))
products_router.put("/{product_id}", to_rsgi(product_update_handler))
products_router.delete("/{product_id}", to_rsgi(product_delete_handler))
products_router.get("/{product_id}/reviews", to_rsgi(product_reviews_handler))
products_router.post("/{product_id}/reviews", to_rsgi(product_review_create_handler))

orders_router = Router()
orders_router.use(user_auth_middleware)
orders_router.get("/", to_rsgi(orders_list_handler))
orders_router.get("/{order_id}", to_rsgi(order_detail_handler))
orders_router.post("/", to_rsgi(order_create_handler))
orders_router.put("/{order_id}/cancel", to_rsgi(order_cancel_handler))
orders_router.get("/{order_id}/invoice", to_rsgi(order_invoice_handler))

cart_router = Router()
cart_router.use(session_middleware)
cart_router.get("/", to_rsgi(cart_view_handler))
cart_router.post("/items", to_rsgi(cart_add_item_handler))
cart_router.put("/items/{item_id}", to_rsgi(cart_update_item_handler))
cart_router.delete("/items/{item_id}", to_rsgi(cart_remove_item_handler))
cart_router.post("/checkout", to_rsgi(cart_checkout_handler))

payments_router = Router()
payments_router.use(user_auth_middleware, payment_security_middleware)
payments_router.post("/process", to_rsgi(payment_process_handler))
payments_router.get("/{payment_id}/status", to_rsgi(payment_status_handler))
payments_router.post("/{payment_id}/refund", to_rsgi(payment_refund_handler))

api_products_router = Router()
api_products_router.get("/", to_rsgi(api_products_handler))
api_products_router.get("/{product_id}", to_rsgi(api_product_handler))
api_products_router.post("/{product_id}/reviews", to_rsgi(api_product_review_handler))
api_products_router.get(
    "/{product_id}/reviews/{review_id}", to_rsgi(api_product_review_detail_handler)
)

api_orders_router = Router()
api_orders_router.get("/", to_rsgi(api_orders_handler))
api_orders_router.get("/{order_id}", to_rsgi(api_order_handler))

api_user_router = Router()
api_user_router.get("/profile", to_rsgi(api_user_profile_handler))

api_v1_router = Router()
api_v1_router.use(rate_limit_middleware, api_auth_middleware)
api_v1_router.not_found(to_rsgi(api_not_found_handler, 404))
api_v1_router.method_not_allowed(to_rsgi(api_method_not_allowed_handler, 405))
api_v1_router.get("/health", to_rsgi(api_health_handler))
api_v1_router.get("/status", to_rsgi(api_status_handler))
api_v1_router.mount("/products", api_products_router)
api_v1_router.mount("/orders", api_orders_router)
api_v1_router.mount("/user", api_user_router)

admin_users_router = Router()
admin_users_router.use(admin_users_permission_middleware)
admin_users_router.get("/", to_rsgi(admin_users_list_handler))
admin_users_router.get("/{user_id}", to_rsgi(admin_user_detail_handler))
admin_users_router.put("/{user_id}", to_rsgi(admin_user_update_handler))
admin_users_router.delete("/{user_id}", to_rsgi(admin_user_delete_handler))
admin_users_router.post("/{user_id}/suspend", to_rsgi(admin_user_suspend_handler))
admin_users_router.post("/{user_id}/activate", to_rsgi(admin_user_activate_handler))
admin_users_router.get("/{user_id}/activity", to_rsgi(admin_user_activity_handler))
admin_users_router.get("/{user_id}/orders", to_rsgi(admin_user_orders_handler))
admin_users_router.get(
    "/{user_id}/orders/{order_id}", to_rsgi(admin_user_order_detail_handler)
)

admin_products_router = Router()
admin_products_router.use(admin_products_permission_middleware)
admin_products_router.get("/", to_rsgi(admin_products_list_handler))
admin_products_router.post("/", to_rsgi(admin_product_create_handler))
admin_products_router.put("/{product_id}", to_rsgi(admin_product_update_handler))
admin_products_router.delete("/{product_id}", to_rsgi(admin_product_delete_handler))
admin_products_router.post(
    "/{product_id}/featured", to_rsgi(admin_product_feature_handler)
)

admin_orders_router = Router()
admin_orders_router.use(admin_orders_permission_middleware)
admin_orders_router.get("/", to_rsgi(admin_orders_list_handler))
admin_orders_router.get("/{order_id}", to_rsgi(admin_order_detail_handler))
admin_orders_router.put("/{order_id}/status", to_rsgi(admin_order_status_handler))
admin_orders_router.post("/{order_id}/refund", to_rsgi(admin_order_refund_handler))

admin_analytics_router = Router()
admin_analytics_router.get("/", to_rsgi(admin_analytics_handler))
admin_analytics_router.get("/revenue", to_rsgi(admin_analytics_revenue_handler))
admin_analytics_router.get("/users", to_rsgi(admin_analytics_users_handler))
admin_analytics_router.get("/products", to_rsgi(admin_analytics_products_handler))

admin_router = Router()
admin_router.use(admin_auth_middleware, admin_logging_middleware)
admin_router.not_found(to_rsgi(admin_not_found_handler, 404))
admin_router.method_not_allowed(to_rsgi(admin_method_not_allowed_handler, 405))
admin_router.get("/", to_rsgi(admin_dashboard_handler))
admin_router.get("/settings", to_rsgi(admin_settings_handler))
admin_router.put("/settings", to_rsgi(admin_settings_update_handler))
admin_router.get("/logs", to_rsgi(admin_logs_handler))
admin_router.get("/logs/{log_id}", to_rsgi(admin_log_detail_handler))
admin_router.mount("/users", admin_users_router)
admin_router.mount("/products", admin_products_router)
admin_router.mount("/orders", admin_orders_router)
admin_router.mount("/analytics", admin_analytics_router)

root_router = Router()
root_router.use(logging_middleware, cors_middleware)
root_router.not_found(to_rsgi(not_found_handler, 404))
root_router.method_not_allowed(to_rsgi(method_not_allowed_handler, 405))
root_router.get("/", to_rsgi(home_handler))
root_router.get("/about", to_rsgi(about_handler))
root_router.get("/contact", to_rsgi(contact_handler))
root_router.post("/contact", to_rsgi(contact_submit_handler))
root_router.get("/pricing", to_rsgi(pricing_handler))
root_router.mount("/static", static_router)
root_router.mount("/uploads", uploads_router)
root_router.mount("/auth", auth_router)
root_router.mount("/user", user_router)
root_router.mount("/dashboard", dashboard_router)
root_router.mount("/products", products_router)
root_router.mount("/orders", orders_router)
root_router.mount("/cart", cart_router)
root_router.mount("/payments", payments_router)
root_router.mount("/api/v1", api_v1_router)
root_router.mount("/admin", admin_router)
root_router.finalize()
