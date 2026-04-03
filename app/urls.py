from django.contrib import admin
from django.urls import path, include
from app import views  # replace with your actual app name

urlpatterns = [
    

    # Homepage,v
    path('', views.index_view, name='index'),

    path('index/', views.index_view, name='index'),
    path('check/',views.check,name='check'),

    # App routes
    path('products/', views.products_view, name='products'),
    path('category/<int:category_id>/', views.products_view, name='products_by_category'),
    path('products/<int:pk>/', views.product_detail, name='product_detail'),
    path('cart/', views.view_cart, name='view_cart'),                       


    path('check/', views.check, name='check'),
    path('payment-instructions/<int:order_id>/', views.payment_instructions, name='payment_instructions'),
    path('brand/<int:brand_id>/', views.products_by_brand, name='products_by_brand'),
    

    # Auth routes
    path('userlog/', views.userlog_view, name='userlog'),
    path('usersignup/', views.usersignup_view, name='usersignup'),
    path('signup/', views.signup_view, name='signup'),
    path('secretkey/', views.secretkey_view, name='secretkey'),
    path('logout/', views.logout_view, name='logout'),
    path('add-to-cart/<int:product_id>/', views.add_to_cart, name='add_to_cart'),

    # Dashboard
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('activity/', views.activity_view, name='activity'),
    path('analytics/', views.analytics_view, name='analytics'),
    path('settings/', views.settings_view, name='settings'),
    path('add_product/', views.add_product, name='add_product'),
    path('manage_products/', views.manage_products, name='manage_products'),
    path('manage_orders/', views.manage_orders, name='manage_orders'),
    path('customers/', views.customers, name='customers'),
    # M-Pesa callback
    path('payment_callback/', views.mpesa_callback, name='mpesa_callback'),
    path('mpesa/register/', views.register_mpesa_urls, name='register_mpesa_urls'),
    # M-Pesa routes

    
    path('update_order_status/<int:order_id>/', views.update_order_status, name='update_order_status'),
    path('update-price/<int:pk>/', views.update_price, name='update_price'),
    path('mark-out-of-stock/<int:product_id>/', views.mark_out_of_stock, name='mark_out_of_stock'),


    # Allauth / Google login
    path('accounts/', include('allauth.urls')),
    path('live-search/', views.live_search, name='live_search'),
    path('update-cart/<int:product_id>/', views.update_cart, name='update_cart'),
    path('remove-from-cart/<int:product_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('change-password/', views.change_password_view, name='change_password'), 
    path('add_admin/',views.add_admin_view,name="add_admin_view"),
    path('increase-cart/<int:item_id>/', views.increase_cart, name='increase_cart'),
    path('decrease-cart/<int:item_id>/', views.decrease_cart, name='decrease_cart'),
    path('remove-cart/<int:item_id>/', views.remove_cart, name='remove_cart'),
    path('search/',views.search_view,name="search")

    
]