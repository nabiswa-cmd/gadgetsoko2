# GadgetSoko 🛒

**GadgetSoko** is a Kenyan e-commerce web application for buying and selling electronics and gadgets. It is built with Django and integrates Safaricom M-Pesa (STK Push) as the primary payment method, making it tailored for the Kenyan market.

---

## Live Deployment

- **Platform:** Vercel / Render
- **URL:** https://gadgetsoko.vercel.app

---

## ✨Features

### Storefront
- Browse products by **category** or **brand**
- Product detail pages with image galleries, specifications, and a live discount countdown timer
- **Live search** — instant results as you type
- **Recommended products** based on browsing history and popularity
- Flash sale / quick-sale section with timed discounts

### Shopping Cart & Checkout
- Add, remove, and update cart items (authenticated users)
- Shipping fee logic: free within Nairobi, max product shipping fee applied for upcountry orders
- Checkout form captures name, phone, delivery region, and address

### Payments — M-Pesa STK Push
- Customers pay via **Lipa Na M-Pesa** (STK Push to their phone)
- Real-time payment callback handling to confirm or fail orders
- Downloadable **PDF receipt** generated after successful payment
- Payment instructions page as fallback

### Authentication
- Standard email/password signup and login
- **Google OAuth** via django-allauth
- Password change functionality

### Admin Dashboard
- Summary stats: total products, orders, users, and revenue
- Manage products (add, edit price, mark out of stock, delete)
- Manage orders and update order status
- View customer list
- Activity feed and analytics page

### Analytics & Tracking
- Per-product view counter
- `UserActivity` log records every view and cart action per user
- `ProductView` tracks which products each user has seen (used for recommendations)

---

## 🏗️ Tech Stack

| Layer | Technology |
|---|---|
| Framework | Django 6.0 |
| Database | SQLite (dev) / PostgreSQL (prod via `dj-database-url`) |
| Authentication | django-allauth (email + Google OAuth) |
| Payments | Safaricom M-Pesa Daraja API (STK Push) |
| PDF Generation | xhtml2pdf + ReportLab |
| Static Files | WhiteNoise |
| Deployment | Gunicorn + Vercel / Render |
| Environment | python-dotenv |

---

## 📁 Project Structure

```
gadgetsoko2/
├── proj/                   # Django project config
│   ├── settings.py         # All settings, reads from .env
│   ├── urls.py             # Root URL routing
│   └── wsgi.py
├── app/                    # Main application
│   ├── models.py           # Brand, Category, Product, Cart, Order, Analytics
│   ├── views.py            # All view functions
│   ├── urls.py             # App URL patterns
│   ├── forms.py            # Signup and other forms
│   ├── mpesa.py            # M-Pesa STK Push helper
│   ├── signals.py          # Auto brand-logo assignment signal
│   ├── context_processors.py  # Cart count injected into all templates
│   ├── admin.py            # Django admin configuration
│   └── templates/          # All HTML templates
├── static/                 # CSS, JS, images
├── media/                  # User-uploaded product images
├── requirements.txt
└── manage.py
```

---

### `.env` file in the project root
```env
SECRET_KEY=your-secure-random-secret-key
DEBUG=True

# M-Pesa Daraja API (Safaricom)
MPESA_CONSUMER_KEY=your_consumer_key
MPESA_CONSUMER_SECRET=your_consumer_secret
MPESA_SHORTCODE=your_shortcode
MPESA_PASSKEY=your_passkey
MPESA_ENV=sandbox
MPESA_CALLBACK_URL=https://yourdomain.com/payment_callback/
SITE_DOMAIN=https://yourdomain.com

# Google OAuth (django-allauth)
CLIENT_ID=your_google_client_id
SECRET_SECRET=your_google_client_secret

# Email (Gmail SMTP)
EMAIL_HOST_USER=your_email@gmail.com
EMAIL_HOST_PASSWORD=your_app_password
```

### 5. Apply migrations and create a superuser
```bash
python manage.py migrate
python manage.py createsuperuser
```

### 6. Collect static files
```bash
python manage.py collectstatic
```

### 7. Run the development server
```bash
python manage.py runserver
```

Visit **http://127.0.0.1:8000** in your browser.

---

## 🔑 Key URLs

| URL | Description |
|---|---|
| `/` | Homepage |
| `/products/` | All products |
| `/category/<id>/` | Products by category |
| `/brand/<id>/` | Products by brand |
| `/products/<id>/` | Product detail |
| `/cart/` | Shopping cart |
| `/check/` | Checkout & M-Pesa payment |
| `/dashboard/` | Admin dashboard |
| `/manage_products/` | Add/edit products |
| `/manage_orders/` | View and update orders |
| `/accounts/google/login/` | Google OAuth login |

---

## 💳 M-Pesa Integration

The app uses the **Safaricom Daraja API** (sandbox by default). To go live:

1. Register at [developer.safaricom.co.ke](https://developer.safaricom.co.ke)
2. Get production credentials and update your `.env`
3. Set `MPESA_ENV=production` in your `.env`
4. Register your callback URL: `GET /mpesa/register/`
5. Ensure your callback URL (`/payment_callback/`) is publicly accessible over HTTPS

---

## 🚀 Deployment (Render / Vercel)

1. Set all `.env` variables as environment variables in your hosting dashboard
2. Set `DEBUG=False` in production
3. Add your domain to `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS` in `settings.py`
4. Run `python manage.py collectstatic` as a build step
5. Use `gunicorn proj.wsgi:application` as the start command

---

## 📦 Data Models

| Model | Purpose |
|---|---|
| `Brand` | Electronics brands (Samsung, Apple, etc.) |
| `Category` | Product categories (Phones, Laptops, etc.) |
| `Product` | Products with price, discount, stock, and shipping fee |
| `ProductImage` | Multiple images per product |
| `CartItem` | Items in a user's active cart |
| `Order` | Customer order with region-based shipping |
| `OrderItem` | Individual line items within an order |
| `UserActivity` | Log of user views and interactions |
| `ProductView` | Tracks which products each user has viewed |
| `SiteSettings` | Global site configuration (discounts toggle, etc.) |

---

## 👤 Author

Developed by **nabiswa-cmd and Sammytings**
GitHub: [github.com/nabiswa-cmd](https://github.com/nabiswa-cmd)

---

