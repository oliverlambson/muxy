"""Mid-sized app structure

router: root_router
    middleware:
        - logging_middleware
        - cors_middleware
    handlers:
        GET   /                     home_handler
        GET   /about                about_handler
        GET   /contact              contact_handler
        POST  /contact              contact_submit_handler
        GET   /pricing              pricing_handler
    not found:
        not_found_handler
    method not allowed:
        method_not_allowed_handler
    mounts:
        /static         static_router
        /uploads        uploads_router
        /auth           auth_router
        /dashboard      dashboard_router
        /products       products_router
        /orders         orders_router
        /cart           cart_router
        /payments       payments_router
        /api/v1         api_v1_router
        /admin          admin_router

router: static_router
    handlers:
        GET  /{path...}            static_handler
    method not allowed:
        static_method_not_allowed_handler

router: uploads_router
    handlers:
        GET  /{path...}            uploads_handler

router: auth_router
    middleware:
        - auth_rate_limit_middleware
    handlers:
        POST  /login                auth_login_handler
        POST  /logout               auth_logout_handler
        POST  /register             auth_register_handler
        POST  /password/reset       auth_password_reset_handler
        POST  /password/change      auth_password_change_handler
        GET   /verify/{token}       auth_verify_handler

router: user_router
    middleware:
        - user_auth_middleware
        - session_middleware
    handlers:
        GET     /profile              user_profile_handler
        PUT     /profile              user_profile_update_handler
        DELETE  /account              user_account_delete_handler
        GET     /settings             user_settings_handler
        POST    /settings             user_settings_update_handler
        GET     /notifications        user_notifications_handler
        PUT     /notifications/{notification_id}   user_notification_update_handler

router: dashboard_router
    middleware:
        - user_auth_middleware
    handlers:
        GET  /                     dashboard_handler
        GET  /stats                dashboard_stats_handler
        GET  /activity             dashboard_activity_handler

router: products_router
    middleware:
        - cache_middleware
    handlers:
    GET     /                           products_list_handler
    GET     /{product_id}               product_detail_handler
    POST    /                           product_create_handler
    PUT     /{product_id}               product_update_handler
    DELETE  /{product_id}               product_delete_handler
    GET     /{product_id}/reviews       product_reviews_handler
    POST    /{product_id}/reviews       product_review_create_handler

router: orders_router
    middleware:
        - user_auth_middleware
    handlers:
        GET   /                         orders_list_handler
        GET   /{order_id}               order_detail_handler
        POST  /                         order_create_handler
        PUT   /{order_id}/cancel        order_cancel_handler
        GET   /{order_id}/invoice       order_invoice_handler

router: cart_router
    middleware:
        - session_middleware
    handlers:
        GET     /                         cart_view_handler
        POST    /items                    cart_add_item_handler
        PUT     /items/{item_id}          cart_update_item_handler
        DELETE  /items/{item_id}          cart_remove_item_handler
        POST    /checkout             cart_checkout_handler

router: payments_router
    middleware:
        - user_auth_middleware
        - payment_security_middleware
    handlers:
    POST  /process                    payment_process_handler
    GET   /{payment_id}/status        payment_status_handler
    POST  /{payment_id}/refund        payment_refund_handler

router: api_v1_router
    middleware:
        - rate_limit_middleware
        - api_auth_middleware
    not found:
        api_not_found_handler
    method not allowed:
        api_method_not_allowed_handler
    handlers:
        GET  /health               api_health_handler
        GET  /status               api_status_handler
    mounts:
        /products       api_products_router
        /orders         api_orders_router
        /user           api_user_router

router: api_products_router
    handlers:
        GET   /                                      api_products_handler
        GET   /{product_id}                          api_product_handler
        POST  /{product_id}/reviews                  api_product_review_handler
        GET   /{product_id}/reviews/{review_id}      api_product_review_detail_handler

router: api_orders_router
    handlers:
    GET  /                  api_orders_handler
    GET  /{order_id}        api_order_handler

router: api_user_router
    handlers:
    GET  /profile           api_user_profile_handler

router: admin_router
    middleware:
        - admin_auth_middleware
        - admin_logging_middleware
    not found:
        admin_not_found_handler
    method not allowed:
        admin_method_not_allowed_handler
    handlers:
        GET  /                     admin_dashboard_handler
        GET  /settings             admin_settings_handler
        PUT  /settings             admin_settings_update_handler
        GET  /logs                 admin_logs_handler
        GET  /logs/{log_id}         admin_log_detail_handler
    mounts:
        /users          admin_users_router
        /products       admin_products_router
        /orders         admin_orders_router
        /analytics      admin_analytics_router

router: admin_users_router
    middleware:
        - admin_users_permission_middleware
    handlers:
        GET     /                                admin_users_list_handler
        GET     /{user_id}                       admin_user_detail_handler
        PUT     /{user_id}                       admin_user_update_handler
        DELETE  /{user_id}                       admin_user_delete_handler
        POST    /{user_id}/suspend               admin_user_suspend_handler
        POST    /{user_id}/activate              admin_user_activate_handler
        GET     /{user_id}/activity              admin_user_activity_handler
        GET     /{user_id}/orders                admin_user_orders_handler
        GET     /{user_id}/orders/{order_id}     admin_user_order_detail_handler

router: admin_products_router
    middleware:
        - admin_products_permission_middleware
    handlers:
        GET     /                          admin_products_list_handler
        POST    /                          admin_product_create_handler
        PUT     /{product_id}              admin_product_update_handler
        DELETE  /{product_id}              admin_product_delete_handler
        POST    /{product_id}/featured     admin_product_feature_handler

router: admin_orders_router
    middleware:
        - admin_orders_permission_middleware
    handlers:
        GET   /                         admin_orders_list_handler
        GET   /{order_id}               admin_order_detail_handler
        PUT   /{order_id}/status        admin_order_status_handler
        POST  /{order_id}/refund        admin_order_refund_handler

router: admin_analytics_router
    handlers:
        GET  /                     admin_analytics_handler
        GET  /revenue              admin_analytics_revenue_handler
        GET  /users                admin_analytics_users_handler
        GET  /products             admin_analytics_products_handler
"""

# handlers
home_handler = lambda: "home"  # noqa: E731
about_handler = lambda: "about"  # noqa: E731
contact_handler = lambda: "contact"  # noqa: E731
contact_submit_handler = lambda: "contact_submit"  # noqa: E731
pricing_handler = lambda: "pricing"  # noqa: E731
static_handler = lambda: "static"  # noqa: E731
uploads_handler = lambda: "uploads"  # noqa: E731
auth_login_handler = lambda: "auth_login"  # noqa: E731
auth_logout_handler = lambda: "auth_logout"  # noqa: E731
auth_register_handler = lambda: "auth_register"  # noqa: E731
auth_password_reset_handler = lambda: "auth_password_reset"  # noqa: E731
auth_password_change_handler = lambda: "auth_password_change"  # noqa: E731
auth_verify_handler = lambda: "auth_verify"  # noqa: E731
user_profile_handler = lambda: "user_profile"  # noqa: E731
user_profile_update_handler = lambda: "user_profile_update"  # noqa: E731
user_account_delete_handler = lambda: "user_account_delete"  # noqa: E731
user_settings_handler = lambda: "user_settings"  # noqa: E731
user_settings_update_handler = lambda: "user_settings_update"  # noqa: E731
user_notifications_handler = lambda: "user_notifications"  # noqa: E731
user_notification_update_handler = lambda: "user_notification_update"  # noqa: E731
dashboard_handler = lambda: "dashboard"  # noqa: E731
dashboard_stats_handler = lambda: "dashboard_stats"  # noqa: E731
dashboard_activity_handler = lambda: "dashboard_activity"  # noqa: E731
products_list_handler = lambda: "products_list"  # noqa: E731
product_detail_handler = lambda: "product_detail"  # noqa: E731
product_create_handler = lambda: "product_create"  # noqa: E731
product_update_handler = lambda: "product_update"  # noqa: E731
product_delete_handler = lambda: "product_delete"  # noqa: E731
product_reviews_handler = lambda: "product_reviews"  # noqa: E731
product_review_create_handler = lambda: "product_review_create"  # noqa: E731
orders_list_handler = lambda: "orders_list"  # noqa: E731
order_detail_handler = lambda: "order_detail"  # noqa: E731
order_create_handler = lambda: "order_create"  # noqa: E731
order_cancel_handler = lambda: "order_cancel"  # noqa: E731
order_invoice_handler = lambda: "order_invoice"  # noqa: E731
cart_view_handler = lambda: "cart_view"  # noqa: E731
cart_add_item_handler = lambda: "cart_add_item"  # noqa: E731
cart_update_item_handler = lambda: "cart_update_item"  # noqa: E731
cart_remove_item_handler = lambda: "cart_remove_item"  # noqa: E731
cart_checkout_handler = lambda: "cart_checkout"  # noqa: E731
payment_process_handler = lambda: "payment_process"  # noqa: E731
payment_status_handler = lambda: "payment_status"  # noqa: E731
payment_refund_handler = lambda: "payment_refund"  # noqa: E731
api_health_handler = lambda: "api_health"  # noqa: E731
api_status_handler = lambda: "api_status"  # noqa: E731
api_products_handler = lambda: "api_products"  # noqa: E731
api_product_handler = lambda: "api_product"  # noqa: E731
api_product_review_handler = lambda: "api_product_review"  # noqa: E731
api_orders_handler = lambda: "api_orders"  # noqa: E731
api_order_handler = lambda: "api_order"  # noqa: E731
api_user_profile_handler = lambda: "api_user_profile"  # noqa: E731
admin_dashboard_handler = lambda: "admin_dashboard"  # noqa: E731
admin_settings_handler = lambda: "admin_settings"  # noqa: E731
admin_settings_update_handler = lambda: "admin_settings_update"  # noqa: E731
admin_logs_handler = lambda: "admin_logs"  # noqa: E731
admin_log_detail_handler = lambda: "admin_log_detail"  # noqa: E731
admin_users_list_handler = lambda: "admin_users_list"  # noqa: E731
admin_user_detail_handler = lambda: "admin_user_detail"  # noqa: E731
admin_user_update_handler = lambda: "admin_user_update"  # noqa: E731
admin_user_delete_handler = lambda: "admin_user_delete"  # noqa: E731
admin_user_suspend_handler = lambda: "admin_user_suspend"  # noqa: E731
admin_user_activate_handler = lambda: "admin_user_activate"  # noqa: E731
admin_user_activity_handler = lambda: "admin_user_activity"  # noqa: E731
admin_user_orders_handler = lambda: "admin_user_orders"  # noqa: E731
admin_products_list_handler = lambda: "admin_products_list"  # noqa: E731
admin_product_create_handler = lambda: "admin_product_create"  # noqa: E731
admin_product_update_handler = lambda: "admin_product_update"  # noqa: E731
admin_product_delete_handler = lambda: "admin_product_delete"  # noqa: E731
admin_product_feature_handler = lambda: "admin_product_feature"  # noqa: E731
admin_orders_list_handler = lambda: "admin_orders_list"  # noqa: E731
admin_order_detail_handler = lambda: "admin_order_detail"  # noqa: E731
admin_order_status_handler = lambda: "admin_order_status"  # noqa: E731
admin_order_refund_handler = lambda: "admin_order_refund"  # noqa: E731
admin_analytics_handler = lambda: "admin_analytics"  # noqa: E731
admin_analytics_revenue_handler = lambda: "admin_analytics_revenue"  # noqa: E731
admin_analytics_users_handler = lambda: "admin_analytics_users"  # noqa: E731
admin_analytics_products_handler = lambda: "admin_analytics_products"  # noqa: E731

# multi-param handlers (for testing routes with multiple parameters)
api_product_review_detail_handler = lambda: "api_product_review_detail"  # noqa: E731
admin_user_order_detail_handler = lambda: "admin_user_order_detail"  # noqa: E731

# middleware
logging_middleware = lambda f: f  # noqa: E731
cors_middleware = lambda f: f  # noqa: E731
auth_rate_limit_middleware = lambda f: f  # noqa: E731
user_auth_middleware = lambda f: f  # noqa: E731
session_middleware = lambda f: f  # noqa: E731
user_auth_middleware = lambda f: f  # noqa: E731
cache_middleware = lambda f: f  # noqa: E731
user_auth_middleware = lambda f: f  # noqa: E731
session_middleware = lambda f: f  # noqa: E731
user_auth_middleware = lambda f: f  # noqa: E731
payment_security_middleware = lambda f: f  # noqa: E731
rate_limit_middleware = lambda f: f  # noqa: E731
api_auth_middleware = lambda f: f  # noqa: E731
admin_auth_middleware = lambda f: f  # noqa: E731
admin_logging_middleware = lambda f: f  # noqa: E731
admin_users_permission_middleware = lambda f: f  # noqa: E731
admin_products_permission_middleware = lambda f: f  # noqa: E731
admin_orders_permission_middleware = lambda f: f  # noqa: E731

# not found
not_found_handler = lambda: "not_found"  # noqa: E731
api_not_found_handler = lambda: "api_not_found"  # noqa: E731
admin_not_found_handler = lambda: "admin_not_found"  # noqa: E731

# method not allowed
method_not_allowed_handler = lambda: "method_not_allowed"  # noqa: E731
static_method_not_allowed_handler = lambda: "static_method_not_allowed"  # noqa: E731
api_method_not_allowed_handler = lambda: "api_method_not_allowed"  # noqa: E731
admin_method_not_allowed_handler = lambda: "admin_method_not_allowed"  # noqa: E731

# router
static_router = {
    "handlers": [
        ("GET", "/{path...}", static_handler),
    ],
    "method not allowed": static_method_not_allowed_handler,
}
uploads_router = {
    "handlers": [
        ("GET", "/{path...}", uploads_handler),
    ]
}
auth_router = {
    "middleware": (auth_rate_limit_middleware,),
    "handlers": [
        ("POST", "/login", auth_login_handler),
        ("POST", "/logout", auth_logout_handler),
        ("POST", "/register", auth_register_handler),
        ("POST", "/password/reset", auth_password_reset_handler),
        ("POST", "/password/change", auth_password_change_handler),
        ("GET", "/verify/{token}", auth_verify_handler),
    ],
}
user_router = {
    "middleware": (user_auth_middleware, session_middleware),
    "handlers": [
        ("GET", "/profile", user_profile_handler),
        ("PUT", "/profile", user_profile_update_handler),
        ("DELETE", "/account", user_account_delete_handler),
        ("GET", "/settings", user_settings_handler),
        ("POST", "/settings", user_settings_update_handler),
        ("GET", "/notifications", user_notifications_handler),
        ("PUT", "/notifications/{notification_id}", user_notification_update_handler),
    ],
}
dashboard_router = {
    "middleware": (user_auth_middleware,),
    "handlers": [
        ("GET", "/", dashboard_handler),
        ("GET", "/stats", dashboard_stats_handler),
        ("GET", "/activity", dashboard_activity_handler),
    ],
}
products_router = {
    "middleware": (cache_middleware,),
    "handlers": [
        ("GET", "/", products_list_handler),
        ("GET", "/{product_id}", product_detail_handler),
        ("POST", "/", product_create_handler),
        ("PUT", "/{product_id}", product_update_handler),
        ("DELETE", "/{product_id}", product_delete_handler),
        ("GET", "/{product_id}/reviews", product_reviews_handler),
        ("POST", "/{product_id}/reviews", product_review_create_handler),
    ],
}
orders_router = {
    "middleware": (user_auth_middleware,),
    "handlers": [
        ("GET", "/", orders_list_handler),
        ("GET", "/{order_id}", order_detail_handler),
        ("POST", "/", order_create_handler),
        ("PUT", "/{order_id}/cancel", order_cancel_handler),
        ("GET", "/{order_id}/invoice", order_invoice_handler),
    ],
}
cart_router = {
    "middleware": (session_middleware,),
    "handlers": [
        ("GET", "/", cart_view_handler),
        ("POST", "/items", cart_add_item_handler),
        ("PUT", "/items/{item_id}", cart_update_item_handler),
        ("DELETE", "/items/{item_id}", cart_remove_item_handler),
        ("POST", "/checkout", cart_checkout_handler),
    ],
}
payments_router = {
    "middleware": (user_auth_middleware, payment_security_middleware),
    "handlers": [
        ("POST", "/process", payment_process_handler),
        ("GET", "/{payment_id}/status", payment_status_handler),
        ("POST", "/{payment_id}/refund", payment_refund_handler),
    ],
}

api_products_router = {
    "handlers": [
        ("GET", "/", api_products_handler),
        ("GET", "/{product_id}", api_product_handler),
        ("POST", "/{product_id}/reviews", api_product_review_handler),
        ("GET", "/{product_id}/reviews/{review_id}", api_product_review_detail_handler),
    ]
}
api_orders_router = {
    "handlers": [
        ("GET", "/", api_orders_handler),
        ("GET", "/{order_id}", api_order_handler),
    ]
}
api_user_router = {
    "handlers": [
        ("GET", "/profile", api_user_profile_handler),
    ]
}
api_v1_router = {
    "middleware": (rate_limit_middleware, api_auth_middleware),
    "not found": api_not_found_handler,
    "method not allowed": api_method_not_allowed_handler,
    "handlers": [
        ("GET", "/health", api_health_handler),
        ("GET", "/status", api_status_handler),
    ],
    "mounts": [
        ("/products", api_products_router),
        ("/orders", api_orders_router),
        ("/user", api_user_router),
    ],
}

admin_users_router = {
    "middleware": (admin_users_permission_middleware,),
    "handlers": [
        ("GET", "/", admin_users_list_handler),
        ("GET", "/{user_id}", admin_user_detail_handler),
        ("PUT", "/{user_id}", admin_user_update_handler),
        ("DELETE", "/{user_id}", admin_user_delete_handler),
        ("POST", "/{user_id}/suspend", admin_user_suspend_handler),
        ("POST", "/{user_id}/activate", admin_user_activate_handler),
        ("GET", "/{user_id}/activity", admin_user_activity_handler),
        ("GET", "/{user_id}/orders", admin_user_orders_handler),
        ("GET", "/{user_id}/orders/{order_id}", admin_user_order_detail_handler),
    ],
}
admin_products_router = {
    "middleware": (admin_products_permission_middleware,),
    "handlers": [
        ("GET", "/", admin_products_list_handler),
        ("POST", "/", admin_product_create_handler),
        ("PUT", "/{product_id}", admin_product_update_handler),
        ("DELETE", "/{product_id}", admin_product_delete_handler),
        ("POST", "/{product_id}/featured", admin_product_feature_handler),
    ],
}
admin_orders_router = {
    "middleware": (admin_orders_permission_middleware,),
    "handlers": [
        ("GET", "/", admin_orders_list_handler),
        ("GET", "/{order_id}", admin_order_detail_handler),
        ("PUT", "/{order_id}/status", admin_order_status_handler),
        ("POST", "/{order_id}/refund", admin_order_refund_handler),
    ],
}
admin_analytics_router = {
    "handlers": [
        ("GET", "/", admin_analytics_handler),
        ("GET", "/revenue", admin_analytics_revenue_handler),
        ("GET", "/users", admin_analytics_users_handler),
        ("GET", "/products", admin_analytics_products_handler),
    ]
}
admin_router = {
    "middleware": (admin_auth_middleware, admin_logging_middleware),
    "not found": admin_not_found_handler,
    "method not allowed": admin_method_not_allowed_handler,
    "handlers": [
        ("GET", "/", admin_dashboard_handler),
        ("GET", "/settings", admin_settings_handler),
        ("PUT", "/settings", admin_settings_update_handler),
        ("GET", "/logs", admin_logs_handler),
        ("GET", "/logs/{log_id}", admin_log_detail_handler),
    ],
    "mounts": [
        ("/users", admin_users_router),
        ("/products", admin_products_router),
        ("/orders", admin_orders_router),
        ("/analytics", admin_analytics_router),
    ],
}

root_router = {
    "middleware": (logging_middleware, cors_middleware),
    "handlers": [
        ("GET", "/", home_handler),
        ("GET", "/about", about_handler),
        ("GET", "/contact", contact_handler),
        ("POST", "/contact", contact_submit_handler),
        ("GET", "/pricing", pricing_handler),
    ],
    "not found": not_found_handler,
    "method not allowed": method_not_allowed_handler,
    "mounts": [
        ("/static", static_router),
        ("/uploads", uploads_router),
        ("/auth", auth_router),
        ("/dashboard", dashboard_router),
        ("/products", products_router),
        ("/orders", orders_router),
        ("/cart", cart_router),
        ("/payments", payments_router),
        ("/api/v1", api_v1_router),
        ("/admin", admin_router),
    ],
}
