"""
To run app:
    uv run granian benchmarks.app.blacksheep:root_router --loop uvloop --interface asgi --port 8086
"""

from collections.abc import Callable
from functools import wraps
from typing import TYPE_CHECKING

from blacksheep import Application, Response, Router, text

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
    pass


def to_blacksheep(h: Callable[[], str]) -> Callable[[], Response]:
    @wraps(h)
    def handler() -> Response:
        return text(h())

    return handler


# Static router (no route-specific middleware, just root middleware)
static_router = Router(prefix="/static")
static_router.add_get(
    "/{path}",
    cors_middleware(logging_middleware(to_blacksheep(static_handler))),
)
_ = static_method_not_allowed_handler  # BlackSheep doesn't have method_not_allowed

# Uploads router (no route-specific middleware, just root middleware)
uploads_router = Router(prefix="/uploads")
uploads_router.add_get(
    "/{path}",
    cors_middleware(logging_middleware(to_blacksheep(uploads_handler))),
)

# Auth router - middleware: auth_rate_limit_middleware
auth_router = Router(prefix="/auth")
auth_router.add_post(
    "/login",
    auth_rate_limit_middleware(
        cors_middleware(logging_middleware(to_blacksheep(auth_login_handler))),
    ),
)
auth_router.add_post(
    "/logout",
    auth_rate_limit_middleware(
        cors_middleware(logging_middleware(to_blacksheep(auth_logout_handler))),
    ),
)
auth_router.add_post(
    "/register",
    auth_rate_limit_middleware(
        cors_middleware(logging_middleware(to_blacksheep(auth_register_handler))),
    ),
)
auth_router.add_post(
    "/password/reset",
    auth_rate_limit_middleware(
        cors_middleware(
            logging_middleware(to_blacksheep(auth_password_reset_handler)),
        ),
    ),
)
auth_router.add_post(
    "/password/change",
    auth_rate_limit_middleware(
        cors_middleware(
            logging_middleware(to_blacksheep(auth_password_change_handler)),
        ),
    ),
)
auth_router.add_get(
    "/verify/{token}",
    auth_rate_limit_middleware(
        cors_middleware(logging_middleware(to_blacksheep(auth_verify_handler))),
    ),
)

# User router - middleware: user_auth_middleware, session_middleware
user_router = Router(prefix="/user")
user_router.add_get(
    "/profile",
    session_middleware(
        user_auth_middleware(
            cors_middleware(logging_middleware(to_blacksheep(user_profile_handler))),
        ),
    ),
)
user_router.add_put(
    "/profile",
    session_middleware(
        user_auth_middleware(
            cors_middleware(
                logging_middleware(to_blacksheep(user_profile_update_handler)),
            ),
        ),
    ),
)
user_router.add_delete(
    "/account",
    session_middleware(
        user_auth_middleware(
            cors_middleware(
                logging_middleware(to_blacksheep(user_account_delete_handler)),
            ),
        ),
    ),
)
user_router.add_get(
    "/settings",
    session_middleware(
        user_auth_middleware(
            cors_middleware(logging_middleware(to_blacksheep(user_settings_handler))),
        ),
    ),
)
user_router.add_post(
    "/settings",
    session_middleware(
        user_auth_middleware(
            cors_middleware(
                logging_middleware(to_blacksheep(user_settings_update_handler)),
            ),
        ),
    ),
)
user_router.add_get(
    "/notifications",
    session_middleware(
        user_auth_middleware(
            cors_middleware(
                logging_middleware(to_blacksheep(user_notifications_handler)),
            ),
        ),
    ),
)
user_router.add_put(
    "/notifications/{notification_id}",
    session_middleware(
        user_auth_middleware(
            cors_middleware(
                logging_middleware(to_blacksheep(user_notification_update_handler)),
            ),
        ),
    ),
)

# Dashboard router - middleware: user_auth_middleware
dashboard_router = Router(prefix="/dashboard")
dashboard_router.add_get(
    "/",
    user_auth_middleware(
        cors_middleware(logging_middleware(to_blacksheep(dashboard_handler))),
    ),
)
dashboard_router.add_get(
    "/stats",
    user_auth_middleware(
        cors_middleware(logging_middleware(to_blacksheep(dashboard_stats_handler))),
    ),
)
dashboard_router.add_get(
    "/activity",
    user_auth_middleware(
        cors_middleware(
            logging_middleware(to_blacksheep(dashboard_activity_handler)),
        ),
    ),
)

# Products router - middleware: cache_middleware
products_router = Router(prefix="/products")
products_router.add_get(
    "/",
    cache_middleware(
        cors_middleware(logging_middleware(to_blacksheep(products_list_handler))),
    ),
)
products_router.add_get(
    "/{product_id}",
    cache_middleware(
        cors_middleware(logging_middleware(to_blacksheep(product_detail_handler))),
    ),
)
products_router.add_post(
    "/",
    cache_middleware(
        cors_middleware(logging_middleware(to_blacksheep(product_create_handler))),
    ),
)
products_router.add_put(
    "/{product_id}",
    cache_middleware(
        cors_middleware(logging_middleware(to_blacksheep(product_update_handler))),
    ),
)
products_router.add_delete(
    "/{product_id}",
    cache_middleware(
        cors_middleware(logging_middleware(to_blacksheep(product_delete_handler))),
    ),
)
products_router.add_get(
    "/{product_id}/reviews",
    cache_middleware(
        cors_middleware(logging_middleware(to_blacksheep(product_reviews_handler))),
    ),
)
products_router.add_post(
    "/{product_id}/reviews",
    cache_middleware(
        cors_middleware(
            logging_middleware(to_blacksheep(product_review_create_handler)),
        ),
    ),
)

# Orders router - middleware: user_auth_middleware
orders_router = Router(prefix="/orders")
orders_router.add_get(
    "/",
    user_auth_middleware(
        cors_middleware(logging_middleware(to_blacksheep(orders_list_handler))),
    ),
)
orders_router.add_get(
    "/{order_id}",
    user_auth_middleware(
        cors_middleware(logging_middleware(to_blacksheep(order_detail_handler))),
    ),
)
orders_router.add_post(
    "/",
    user_auth_middleware(
        cors_middleware(logging_middleware(to_blacksheep(order_create_handler))),
    ),
)
orders_router.add_put(
    "/{order_id}/cancel",
    user_auth_middleware(
        cors_middleware(logging_middleware(to_blacksheep(order_cancel_handler))),
    ),
)
orders_router.add_get(
    "/{order_id}/invoice",
    user_auth_middleware(
        cors_middleware(logging_middleware(to_blacksheep(order_invoice_handler))),
    ),
)

# Cart router - middleware: session_middleware
cart_router = Router(prefix="/cart")
cart_router.add_get(
    "/",
    session_middleware(
        cors_middleware(logging_middleware(to_blacksheep(cart_view_handler))),
    ),
)
cart_router.add_post(
    "/items",
    session_middleware(
        cors_middleware(logging_middleware(to_blacksheep(cart_add_item_handler))),
    ),
)
cart_router.add_put(
    "/items/{item_id}",
    session_middleware(
        cors_middleware(logging_middleware(to_blacksheep(cart_update_item_handler))),
    ),
)
cart_router.add_delete(
    "/items/{item_id}",
    session_middleware(
        cors_middleware(logging_middleware(to_blacksheep(cart_remove_item_handler))),
    ),
)
cart_router.add_post(
    "/checkout",
    session_middleware(
        cors_middleware(logging_middleware(to_blacksheep(cart_checkout_handler))),
    ),
)

# Payments router - middleware: user_auth_middleware, payment_security_middleware
payments_router = Router(prefix="/payments")
payments_router.add_post(
    "/process",
    payment_security_middleware(
        user_auth_middleware(
            cors_middleware(logging_middleware(to_blacksheep(payment_process_handler))),
        ),
    ),
)
payments_router.add_get(
    "/{payment_id}/status",
    payment_security_middleware(
        user_auth_middleware(
            cors_middleware(logging_middleware(to_blacksheep(payment_status_handler))),
        ),
    ),
)
payments_router.add_post(
    "/{payment_id}/refund",
    payment_security_middleware(
        user_auth_middleware(
            cors_middleware(logging_middleware(to_blacksheep(payment_refund_handler))),
        ),
    ),
)

# API products router (inherits api_v1 middleware)
api_products_router = Router(prefix="/products")
api_products_router.add_get(
    "/",
    api_auth_middleware(
        rate_limit_middleware(
            cors_middleware(logging_middleware(to_blacksheep(api_products_handler))),
        ),
    ),
)
api_products_router.add_get(
    "/{product_id}",
    api_auth_middleware(
        rate_limit_middleware(
            cors_middleware(logging_middleware(to_blacksheep(api_product_handler))),
        ),
    ),
)
api_products_router.add_post(
    "/{product_id}/reviews",
    api_auth_middleware(
        rate_limit_middleware(
            cors_middleware(
                logging_middleware(to_blacksheep(api_product_review_handler)),
            ),
        ),
    ),
)
api_products_router.add_get(
    "/{product_id}/reviews/{review_id}",
    api_auth_middleware(
        rate_limit_middleware(
            cors_middleware(
                logging_middleware(to_blacksheep(api_product_review_detail_handler)),
            ),
        ),
    ),
)

# API orders router (inherits api_v1 middleware)
api_orders_router = Router(prefix="/orders")
api_orders_router.add_get(
    "/",
    api_auth_middleware(
        rate_limit_middleware(
            cors_middleware(logging_middleware(to_blacksheep(api_orders_handler))),
        ),
    ),
)
api_orders_router.add_get(
    "/{order_id}",
    api_auth_middleware(
        rate_limit_middleware(
            cors_middleware(logging_middleware(to_blacksheep(api_order_handler))),
        ),
    ),
)

# API user router (inherits api_v1 middleware)
api_user_router = Router(prefix="/user")
api_user_router.add_get(
    "/profile",
    api_auth_middleware(
        rate_limit_middleware(
            cors_middleware(
                logging_middleware(to_blacksheep(api_user_profile_handler))
            ),
        ),
    ),
)

# API v1 router - middleware: rate_limit_middleware, api_auth_middleware
api_v1_router = Router(
    prefix="/api/v1",
    sub_routers=[api_products_router, api_orders_router, api_user_router],
)
api_v1_router.add_get(
    "/health",
    api_auth_middleware(
        rate_limit_middleware(
            cors_middleware(logging_middleware(to_blacksheep(api_health_handler))),
        ),
    ),
)
api_v1_router.add_get(
    "/status",
    api_auth_middleware(
        rate_limit_middleware(
            cors_middleware(logging_middleware(to_blacksheep(api_status_handler))),
        ),
    ),
)
# Note: sub-router fallbacks interfere with parent routing in BlackSheep
_ = api_not_found_handler
_ = api_method_not_allowed_handler

# Admin users router - middleware: admin_users_permission_middleware (+ admin middleware)
admin_users_router = Router(prefix="/users")
admin_users_router.add_get(
    "/",
    admin_users_permission_middleware(
        admin_logging_middleware(
            admin_auth_middleware(
                cors_middleware(
                    logging_middleware(to_blacksheep(admin_users_list_handler))
                ),
            ),
        ),
    ),
)
admin_users_router.add_get(
    "/{user_id}",
    admin_users_permission_middleware(
        admin_logging_middleware(
            admin_auth_middleware(
                cors_middleware(
                    logging_middleware(to_blacksheep(admin_user_detail_handler))
                ),
            ),
        ),
    ),
)
admin_users_router.add_put(
    "/{user_id}",
    admin_users_permission_middleware(
        admin_logging_middleware(
            admin_auth_middleware(
                cors_middleware(
                    logging_middleware(to_blacksheep(admin_user_update_handler))
                ),
            ),
        ),
    ),
)
admin_users_router.add_delete(
    "/{user_id}",
    admin_users_permission_middleware(
        admin_logging_middleware(
            admin_auth_middleware(
                cors_middleware(
                    logging_middleware(to_blacksheep(admin_user_delete_handler))
                ),
            ),
        ),
    ),
)
admin_users_router.add_post(
    "/{user_id}/suspend",
    admin_users_permission_middleware(
        admin_logging_middleware(
            admin_auth_middleware(
                cors_middleware(
                    logging_middleware(to_blacksheep(admin_user_suspend_handler))
                ),
            ),
        ),
    ),
)
admin_users_router.add_post(
    "/{user_id}/activate",
    admin_users_permission_middleware(
        admin_logging_middleware(
            admin_auth_middleware(
                cors_middleware(
                    logging_middleware(to_blacksheep(admin_user_activate_handler))
                ),
            ),
        ),
    ),
)
admin_users_router.add_get(
    "/{user_id}/activity",
    admin_users_permission_middleware(
        admin_logging_middleware(
            admin_auth_middleware(
                cors_middleware(
                    logging_middleware(to_blacksheep(admin_user_activity_handler))
                ),
            ),
        ),
    ),
)
admin_users_router.add_get(
    "/{user_id}/orders",
    admin_users_permission_middleware(
        admin_logging_middleware(
            admin_auth_middleware(
                cors_middleware(
                    logging_middleware(to_blacksheep(admin_user_orders_handler))
                ),
            ),
        ),
    ),
)
admin_users_router.add_get(
    "/{user_id}/orders/{order_id}",
    admin_users_permission_middleware(
        admin_logging_middleware(
            admin_auth_middleware(
                cors_middleware(
                    logging_middleware(to_blacksheep(admin_user_order_detail_handler)),
                ),
            ),
        ),
    ),
)

# Admin products router - middleware: admin_products_permission_middleware (+ admin middleware)
admin_products_router = Router(prefix="/products")
admin_products_router.add_get(
    "/",
    admin_products_permission_middleware(
        admin_logging_middleware(
            admin_auth_middleware(
                cors_middleware(
                    logging_middleware(to_blacksheep(admin_products_list_handler))
                ),
            ),
        ),
    ),
)
admin_products_router.add_post(
    "/",
    admin_products_permission_middleware(
        admin_logging_middleware(
            admin_auth_middleware(
                cors_middleware(
                    logging_middleware(to_blacksheep(admin_product_create_handler))
                ),
            ),
        ),
    ),
)
admin_products_router.add_put(
    "/{product_id}",
    admin_products_permission_middleware(
        admin_logging_middleware(
            admin_auth_middleware(
                cors_middleware(
                    logging_middleware(to_blacksheep(admin_product_update_handler))
                ),
            ),
        ),
    ),
)
admin_products_router.add_delete(
    "/{product_id}",
    admin_products_permission_middleware(
        admin_logging_middleware(
            admin_auth_middleware(
                cors_middleware(
                    logging_middleware(to_blacksheep(admin_product_delete_handler))
                ),
            ),
        ),
    ),
)
admin_products_router.add_post(
    "/{product_id}/featured",
    admin_products_permission_middleware(
        admin_logging_middleware(
            admin_auth_middleware(
                cors_middleware(
                    logging_middleware(to_blacksheep(admin_product_feature_handler))
                ),
            ),
        ),
    ),
)

# Admin orders router - middleware: admin_orders_permission_middleware (+ admin middleware)
admin_orders_router = Router(prefix="/orders")
admin_orders_router.add_get(
    "/",
    admin_orders_permission_middleware(
        admin_logging_middleware(
            admin_auth_middleware(
                cors_middleware(
                    logging_middleware(to_blacksheep(admin_orders_list_handler))
                ),
            ),
        ),
    ),
)
admin_orders_router.add_get(
    "/{order_id}",
    admin_orders_permission_middleware(
        admin_logging_middleware(
            admin_auth_middleware(
                cors_middleware(
                    logging_middleware(to_blacksheep(admin_order_detail_handler))
                ),
            ),
        ),
    ),
)
admin_orders_router.add_put(
    "/{order_id}/status",
    admin_orders_permission_middleware(
        admin_logging_middleware(
            admin_auth_middleware(
                cors_middleware(
                    logging_middleware(to_blacksheep(admin_order_status_handler))
                ),
            ),
        ),
    ),
)
admin_orders_router.add_post(
    "/{order_id}/refund",
    admin_orders_permission_middleware(
        admin_logging_middleware(
            admin_auth_middleware(
                cors_middleware(
                    logging_middleware(to_blacksheep(admin_order_refund_handler))
                ),
            ),
        ),
    ),
)

# Admin analytics router (just admin middleware, no extra)
admin_analytics_router = Router(prefix="/analytics")
admin_analytics_router.add_get(
    "/",
    admin_logging_middleware(
        admin_auth_middleware(
            cors_middleware(logging_middleware(to_blacksheep(admin_analytics_handler))),
        ),
    ),
)
admin_analytics_router.add_get(
    "/revenue",
    admin_logging_middleware(
        admin_auth_middleware(
            cors_middleware(
                logging_middleware(to_blacksheep(admin_analytics_revenue_handler))
            ),
        ),
    ),
)
admin_analytics_router.add_get(
    "/users",
    admin_logging_middleware(
        admin_auth_middleware(
            cors_middleware(
                logging_middleware(to_blacksheep(admin_analytics_users_handler))
            ),
        ),
    ),
)
admin_analytics_router.add_get(
    "/products",
    admin_logging_middleware(
        admin_auth_middleware(
            cors_middleware(
                logging_middleware(to_blacksheep(admin_analytics_products_handler))
            ),
        ),
    ),
)

# Admin router - middleware: admin_auth_middleware, admin_logging_middleware
admin_router = Router(
    prefix="/admin",
    sub_routers=[
        admin_users_router,
        admin_products_router,
        admin_orders_router,
        admin_analytics_router,
    ],
)
admin_router.add_get(
    "/",
    admin_logging_middleware(
        admin_auth_middleware(
            cors_middleware(logging_middleware(to_blacksheep(admin_dashboard_handler))),
        ),
    ),
)
admin_router.add_get(
    "/settings",
    admin_logging_middleware(
        admin_auth_middleware(
            cors_middleware(logging_middleware(to_blacksheep(admin_settings_handler))),
        ),
    ),
)
admin_router.add_put(
    "/settings",
    admin_logging_middleware(
        admin_auth_middleware(
            cors_middleware(
                logging_middleware(to_blacksheep(admin_settings_update_handler))
            ),
        ),
    ),
)
admin_router.add_get(
    "/logs",
    admin_logging_middleware(
        admin_auth_middleware(
            cors_middleware(logging_middleware(to_blacksheep(admin_logs_handler))),
        ),
    ),
)
admin_router.add_get(
    "/logs/{log_id}",
    admin_logging_middleware(
        admin_auth_middleware(
            cors_middleware(
                logging_middleware(to_blacksheep(admin_log_detail_handler))
            ),
        ),
    ),
)
# Note: sub-router fallbacks interfere with parent routing in BlackSheep
_ = admin_not_found_handler
_ = admin_method_not_allowed_handler

# Main router - middleware: logging_middleware, cors_middleware (root level)
main_router = Router(
    sub_routers=[
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
)
main_router.add_get(
    "/", cors_middleware(logging_middleware(to_blacksheep(home_handler)))
)
main_router.add_get(
    "/about", cors_middleware(logging_middleware(to_blacksheep(about_handler)))
)
main_router.add_get(
    "/contact",
    cors_middleware(logging_middleware(to_blacksheep(contact_handler))),
)
main_router.add_post(
    "/contact",
    cors_middleware(logging_middleware(to_blacksheep(contact_submit_handler))),
)
main_router.add_get(
    "/pricing",
    cors_middleware(logging_middleware(to_blacksheep(pricing_handler))),
)

# Set fallback (404 handler)
main_router.fallback = cors_middleware(
    logging_middleware(to_blacksheep(not_found_handler))
)
_ = method_not_allowed_handler  # BlackSheep doesn't have method_not_allowed

# Root application
root_router = Application(router=main_router, show_error_details=False)
