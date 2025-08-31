from __future__ import annotations

from decimal import Decimal
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _


class Wallet(models.Model):
    """کیف پول کاربر"""
    user = models.OneToOneField(
        'users.User',
        on_delete=models.CASCADE,
        related_name='wallet',
        verbose_name=_("User")
    )
    balance = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name=_("Balance")
    )
    currency = models.CharField(
        max_length=3,
        default='USD',
        verbose_name=_("Currency")
    )
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Last Updated"))

    class Meta:
        verbose_name = _("Wallet")
        verbose_name_plural = _("Wallets")

    def __str__(self):
        return f"{self.user.full_name}'s Wallet ({self.balance} {self.currency})"

    def can_afford(self, amount: Decimal) -> bool:
        """بررسی اینکه آیا کاربر می‌تواند این مبلغ را پرداخت کند"""
        return self.balance >= amount

    def add_funds(self, amount: Decimal) -> None:
        """افزودن پول به کیف پول"""
        if amount <= 0:
            raise ValueError("Amount must be positive")
        self.balance += amount
        self.save()

    def deduct_funds(self, amount: Decimal) -> bool:
        """کسر پول از کیف پول"""
        if amount <= 0:
            raise ValueError("Amount must be positive")
        if not self.can_afford(amount):
            return False
        self.balance -= amount
        self.save()
        return True


class Category(models.Model):
    """دسته‌بندی محصولات - خودارجاعی برای دسته‌بندی چندسطحی"""
    name = models.CharField(max_length=100, verbose_name=_("Category Name"))
    slug = models.SlugField(unique=True, verbose_name=_("Slug"))
    description = models.TextField(blank=True, verbose_name=_("Description"))
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='children',
        verbose_name=_("Parent Category")
    )
    is_active = models.BooleanField(default=True, verbose_name=_("Active"))
    order = models.PositiveIntegerField(default=0, verbose_name=_("Display Order"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated At"))

    class Meta:
        ordering = ['order', 'name']
        verbose_name = _("Category")
        verbose_name_plural = _("Categories")

    def __str__(self):
        if self.parent:
            return f"{self.parent.name} > {self.name}"
        return self.name

    @property
    def is_root(self) -> bool:
        """آیا این دسته‌بندی ریشه است؟"""
        return self.parent is None

    @property
    def level(self) -> int:
        """سطح دسته‌بندی (0 برای ریشه)"""
        if self.is_root:
            return 0
        return self.parent.level + 1


class Product(models.Model):
    """محصولات علمی"""
    seller = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE,
        related_name='products',
        verbose_name=_("Seller")
    )
    title = models.CharField(max_length=200, verbose_name=_("Product Title"))
    slug = models.SlugField(unique=True, verbose_name=_("Slug"))
    description = models.TextField(verbose_name=_("Description"))
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name='products',
        verbose_name=_("Category")
    )
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        verbose_name=_("Price")
    )
    stock = models.PositiveIntegerField(default=0, verbose_name=_("Stock"))
    file_path = models.FileField(
        upload_to='products/',
        verbose_name=_("Product File")
    )
    file_size = models.PositiveIntegerField(
        help_text=_("File size in bytes"),
        verbose_name=_("File Size")
    )
    preview_image = models.ImageField(
        upload_to='products/previews/',
        blank=True,
        null=True,
        verbose_name=_("Preview Image")
    )
    is_active = models.BooleanField(default=True, verbose_name=_("Active"))
    is_featured = models.BooleanField(default=False, verbose_name=_("Featured"))
    download_count = models.PositiveIntegerField(default=0, verbose_name=_("Download Count"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated At"))

    class Meta:
        ordering = ['-created_at']
        verbose_name = _("Product")
        verbose_name_plural = _("Products")

    def __str__(self):
        return self.title

    @property
    def is_available(self) -> bool:
        """آیا محصول موجود است؟"""
        return self.is_active and self.stock > 0

    def decrease_stock(self, quantity: int = 1) -> bool:
        """کاهش موجودی محصول"""
        if self.stock >= quantity:
            self.stock -= quantity
            self.save()
            return True
        return False

    def increase_stock(self, quantity: int = 1) -> None:
        """افزایش موجودی محصول"""
        self.stock += quantity
        self.save()


class Order(models.Model):
    """سفارش‌ها"""
    class Status(models.TextChoices):
        PENDING = "pending", _("Pending")
        PAID = "paid", _("Paid")
        SHIPPED = "shipped", _("Shipped")
        DELIVERED = "delivered", _("Delivered")
        CANCELED = "canceled", _("Canceled")
        REFUNDED = "refunded", _("Refunded")

    buyer = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE,
        related_name='orders',
        verbose_name=_("Buyer")
    )
    order_number = models.CharField(
        max_length=20,
        unique=True,
        verbose_name=_("Order Number")
    )
    total_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        verbose_name=_("Total Price")
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        verbose_name=_("Status")
    )
    notes = models.TextField(blank=True, verbose_name=_("Order Notes"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated At"))

    class Meta:
        ordering = ['-created_at']
        verbose_name = _("Order")
        verbose_name_plural = _("Orders")

    def __str__(self):
        return f"Order {self.order_number} - {self.buyer.full_name}"

    def save(self, *args, **kwargs):
        if not self.order_number:
            # تولید شماره سفارش خودکار
            import uuid
            self.order_number = f"ORD-{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)

    @property
    def can_cancel(self) -> bool:
        """آیا سفارش قابل لغو است؟"""
        return self.status in [self.Status.PENDING, self.Status.PAID]

    @property
    def can_refund(self) -> bool:
        """آیا سفارش قابل بازگشت وجه است؟"""
        return self.status in [self.Status.PAID, self.Status.SHIPPED, self.Status.DELIVERED]


class OrderItem(models.Model):
    """جزئیات سفارش"""
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name=_("Order")
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name='order_items',
        verbose_name=_("Product")
    )
    quantity = models.PositiveIntegerField(
        default=1,
        validators=[MinValueValidator(1)],
        verbose_name=_("Quantity")
    )
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        verbose_name=_("Unit Price")
    )
    total_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name=_("Total Price")
    )

    class Meta:
        verbose_name = _("Order Item")
        verbose_name_plural = _("Order Items")

    def __str__(self):
        return f"{self.quantity}x {self.product.title} in Order {self.order.order_number}"

    def save(self, *args, **kwargs):
        # محاسبه خودکار قیمت کل
        self.total_price = self.quantity * self.price
        super().save(*args, **kwargs)


class Transaction(models.Model):
    """تاریخچه تراکنش‌ها"""
    class Type(models.TextChoices):
        DEPOSIT = "deposit", _("Deposit")
        WITHDRAW = "withdraw", _("Withdraw")
        PURCHASE = "purchase", _("Purchase")
        REFUND = "refund", _("Refund")
        TRANSFER = "transfer", _("Transfer")

    wallet = models.ForeignKey(
        Wallet,
        on_delete=models.CASCADE,
        related_name='transactions',
        verbose_name=_("Wallet")
    )
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name=_("Amount")
    )
    type = models.CharField(
        max_length=20,
        choices=Type.choices,
        verbose_name=_("Transaction Type")
    )
    description = models.CharField(
        max_length=255,
        blank=True,
        verbose_name=_("Description")
    )
    reference_id = models.CharField(
        max_length=100,
        blank=True,
        help_text=_("External reference ID (payment gateway, etc.)"),
        verbose_name=_("Reference ID")
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))

    class Meta:
        ordering = ['-created_at']
        verbose_name = _("Transaction")
        verbose_name_plural = _("Transactions")

    def __str__(self):
        return f"{self.type} - {self.amount} ({self.wallet.currency})"


class Ticket(models.Model):
    """پشتیبانی/تیکت‌ها"""
    class Status(models.TextChoices):
        OPEN = "open", _("Open")
        IN_PROGRESS = "in_progress", _("In Progress")
        WAITING_FOR_USER = "waiting_for_user", _("Waiting for User")
        CLOSED = "closed", _("Closed")

    class Priority(models.TextChoices):
        LOW = "low", _("Low")
        MEDIUM = "medium", _("Medium")
        HIGH = "high", _("High")
        URGENT = "urgent", _("Urgent")

    user = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE,
        related_name='tickets',
        verbose_name=_("User")
    )
    subject = models.CharField(max_length=200, verbose_name=_("Subject"))
    message = models.TextField(verbose_name=_("Message"))
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.OPEN,
        verbose_name=_("Status")
    )
    priority = models.CharField(
        max_length=20,
        choices=Priority.choices,
        default=Priority.MEDIUM,
        verbose_name=_("Priority")
    )
    assigned_to = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_tickets',
        verbose_name=_("Assigned To")
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated At"))

    class Meta:
        ordering = ['-created_at']
        verbose_name = _("Ticket")
        verbose_name_plural = _("Tickets")

    def __str__(self):
        return f"Ticket #{self.id}: {self.subject}"


class Review(models.Model):
    """نظرات کاربران"""
    user = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE,
        related_name='reviews',
        verbose_name=_("User")
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='reviews',
        verbose_name=_("Product")
    )
    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        verbose_name=_("Rating")
    )
    comment = models.TextField(verbose_name=_("Comment"))
    is_verified_purchase = models.BooleanField(
        default=False,
        verbose_name=_("Verified Purchase")
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated At"))

    class Meta:
        unique_together = ['user', 'product']  # هر کاربر فقط یک نظر per محصول
        ordering = ['-created_at']
        verbose_name = _("Review")
        verbose_name_plural = _("Reviews")

    def __str__(self):
        return f"{self.user.full_name}'s review on {self.product.title}"


class AuditLog(models.Model):
    """لاگ امنیتی/دسترسی"""
    class Action(models.TextChoices):
        LOGIN = "login", _("Login")
        LOGOUT = "logout", _("Logout")
        CREATE = "create", _("Create")
        UPDATE = "update", _("Update")
        DELETE = "delete", _("Delete")
        VIEW = "view", _("View")
        DOWNLOAD = "download", _("Download")
        PAYMENT = "payment", _("Payment")

    user = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_logs',
        verbose_name=_("User")
    )
    action = models.CharField(
        max_length=20,
        choices=Action.choices,
        verbose_name=_("Action")
    )
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        verbose_name=_("IP Address")
    )
    user_agent = models.TextField(
        blank=True,
        verbose_name=_("User Agent")
    )
    resource_type = models.CharField(
        max_length=50,
        blank=True,
        help_text=_("Type of resource being accessed (User, Product, etc.)"),
        verbose_name=_("Resource Type")
    )
    resource_id = models.CharField(
        max_length=50,
        blank=True,
        help_text=_("ID of the resource being accessed"),
        verbose_name=_("Resource ID")
    )
    details = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_("Additional Details")
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))

    class Meta:
        ordering = ['-created_at']
        verbose_name = _("Audit Log")
        verbose_name_plural = _("Audit Logs")

    def __str__(self):
        return f"{self.action} by {self.user.full_name if self.user else 'Anonymous'} at {self.created_at}"
