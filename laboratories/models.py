from django.conf import settings
from django.contrib.auth.models import AbstractUser, Group
from django.core.validators import FileExtensionValidator, MaxValueValidator, MinValueValidator
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify


class User(AbstractUser):
    ROLE_CHOICES = (
        ('super_admin', 'Super Admin'),
        ('lab_admin', 'Lab Admin'),
        ('company_user', 'Company User'),
        ('admin', 'Admin'),
        ('company', 'Company'),
        ('user', 'User'),
    )

    name = models.CharField(max_length=100, blank=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='company_user')
    is_verified = models.BooleanField(default=False)
    verification_token = models.CharField(max_length=100, blank=True)
    profile_image = models.ImageField(upload_to='profiles/', blank=True, null=True)

    def save(self, *args, **kwargs):
        if not self.name and (self.first_name or self.last_name):
            self.name = f"{self.first_name} {self.last_name}".strip()
        if self.is_superuser:
            self.role = 'super_admin'
        else:
            self.role = self.normalize_role(self.role)
        super().save(*args, **kwargs)
        self.sync_role_group()

    def normalize_role(self, role):
        if not role:
            return 'company_user'
        role_map = {
            'super_admin': 'super_admin',
            'lab_admin': 'lab_admin',
            'company_user': 'company_user',
            'company': 'company_user',
            'user': 'company_user',
            'admin': 'lab_admin',
        }
        return role_map.get(role, 'company_user')

    @property
    def normalized_role(self):
        return self.normalize_role(self.role)

    @property
    def is_super_admin(self):
        return self.is_superuser or self.normalized_role == 'super_admin'

    @property
    def is_lab_admin(self):
        return self.is_super_admin or self.normalized_role == 'lab_admin'

    @property
    def is_company_user(self):
        return self.is_super_admin or self.normalized_role == 'company_user'

    @property
    def role_label(self):
        return dict(self.ROLE_CHOICES).get(self.normalized_role, self.normalized_role.replace('_', ' ').title())

    def get_role_group_name(self):
        if self.is_super_admin:
            return 'Super Admin'
        if self.is_lab_admin:
            return 'Lab Admin'
        if self.is_company_user:
            return 'Company User'
        return 'Company User'

    def sync_role_group(self):
        group_name = self.get_role_group_name()
        if group_name:
            group, _ = Group.objects.get_or_create(name=group_name)
            self.groups.set([group])

    def __str__(self):
        return self.username or self.email


class Category(models.Model):
    category_name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True, blank=True)
    description = models.TextField(blank=True)

    class Meta:
        verbose_name_plural = 'Categories'

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.category_name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.category_name


class Laboratory(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='laboratories', on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, blank=True)
    description = models.TextField()
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    address = models.CharField(max_length=255)
    phone = models.CharField(max_length=20)
    email = models.EmailField()
    website = models.URLField(blank=True)
    accreditation = models.CharField(max_length=200, blank=True)
    accreditation_certificate = models.FileField(upload_to='accreditation_certificates/', blank=True, null=True)
    categories = models.ManyToManyField(Category, related_name='laboratories', blank=True)
    is_approved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    @property
    def average_rating(self):
        reviews = self.reviews.all()
        if not reviews.exists():
            return 0
        return round(sum(review.rating for review in reviews) / reviews.count(), 1)

    def get_absolute_url(self):
        return reverse('laboratory-detail', kwargs={'slug': self.slug})

    def __str__(self):
        return self.name


class AccreditationCertificate(models.Model):
    laboratory = models.ForeignKey(Laboratory, related_name='certificates', on_delete=models.CASCADE)
    image = models.ImageField(
        upload_to='accreditation_certificates/',
        validators=[FileExtensionValidator(['jpg', 'jpeg', 'png', 'webp'])],
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-uploaded_at']

    def __str__(self):
        return f"{self.laboratory.name} certificate"


class Appointment(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    )

    laboratory = models.ForeignKey(Laboratory, related_name='appointments', on_delete=models.CASCADE)
    full_name = models.CharField(max_length=150)
    contact_number = models.CharField(max_length=30)
    email_address = models.EmailField()
    appointment_date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-appointment_date', '-created_at']

    @property
    def reference_number(self):
        return f"APT-{self.pk:06d}"

    def __str__(self):
        return f"{self.full_name} @ {self.laboratory.name} on {self.appointment_date}"


class FavoriteLaboratory(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='favorite_laboratories', on_delete=models.CASCADE)
    laboratory = models.ForeignKey(Laboratory, related_name='favorited_by', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'laboratory')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user} favorites {self.laboratory.name}"


class QuotationRequest(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('received', 'Received'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
    )

    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='quotation_requests', on_delete=models.CASCADE)
    laboratory = models.ForeignKey(Laboratory, related_name='quotation_requests', on_delete=models.SET_NULL, null=True, blank=True)
    subject = models.CharField(max_length=200, blank=True)
    test_type = models.CharField(max_length=200, blank=True)
    product_or_sample_details = models.TextField(blank=True)
    company_name = models.CharField(max_length=200, blank=True)
    contact_name = models.CharField(max_length=150, blank=True)
    contact_email = models.EmailField(blank=True)
    contact_phone = models.CharField(max_length=30, blank=True)
    location = models.CharField(max_length=200, blank=True)
    preferred_timeline = models.CharField(max_length=100, blank=True)
    message = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    quote_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    lab_response = models.TextField(blank=True)
    responded_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.subject and self.test_type:
            self.subject = f"Quote request for {self.test_type}"
        super().save(*args, **kwargs)

    @property
    def latest_lab_message(self):
        return self.messages.select_related('sender').filter(sender__role__in=['lab_admin', 'super_admin']).order_by('-created_at').first()

    @property
    def latest_lab_message_preview(self):
        message = self.latest_lab_message
        if not message:
            return 'No lab update yet.'
        return message.message[:80] + ('…' if len(message.message) > 80 else '')

    def get_unread_count_for(self, user):
        return self.messages.filter(recipient=user, is_read=False).count()

    def mark_messages_read_for(self, user):
        self.messages.filter(recipient=user, is_read=False).update(is_read=True)

    def __str__(self):
        return self.subject or self.test_type or 'Quotation request'


class QuoteMessage(models.Model):
    MESSAGE_TYPES = (
        ('message', 'Message'),
        ('quotation', 'Quotation'),
        ('info_request', 'Request for additional information'),
        ('status_update', 'Status update'),
    )

    quote_request = models.ForeignKey(QuotationRequest, related_name='messages', on_delete=models.CASCADE)
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='sent_quote_messages', on_delete=models.CASCADE)
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='received_quote_messages', on_delete=models.SET_NULL, null=True, blank=True)
    message = models.TextField()
    message_type = models.CharField(max_length=20, choices=MESSAGE_TYPES, default='message')
    quote_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['created_at']

    @property
    def is_lab_message(self):
        return self.sender.is_lab_admin or self.sender.is_super_admin

    @property
    def sender_display(self):
        return self.sender.get_full_name() or self.sender.username or self.sender.email

    def __str__(self):
        return f"{self.sender_display}: {self.message[:60]}"


class ComplianceReminder(models.Model):
    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='compliance_reminders', on_delete=models.CASCADE)
    laboratory = models.ForeignKey(Laboratory, related_name='compliance_reminders', on_delete=models.SET_NULL, null=True, blank=True)
    title = models.CharField(max_length=200)
    due_date = models.DateField()
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['due_date', 'created_at']

    def __str__(self):
        return self.title


class Review(models.Model):
    laboratory = models.ForeignKey(Laboratory, related_name='reviews', on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='reviews', on_delete=models.CASCADE)
    rating = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    review_text = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.rating} stars"


class TestReport(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('uploaded', 'Uploaded'),
        ('reviewed', 'Reviewed'),
        ('completed', 'Completed'),
    )

    laboratory = models.ForeignKey(Laboratory, related_name='test_reports', on_delete=models.CASCADE)
    appointment = models.ForeignKey(Appointment, related_name='test_reports', on_delete=models.SET_NULL, null=True, blank=True)
    title = models.CharField(max_length=200)
    file = models.FileField(upload_to='test_reports/', blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='uploaded')
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='uploaded_reports', on_delete=models.SET_NULL, null=True, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-uploaded_at']

    def __str__(self):
        return self.title


class ContactInquiry(models.Model):
    STATUS_CHOICES = (
        ('new', 'New'),
        ('contacted', 'Contacted'),
        ('qualified', 'Qualified'),
        ('converted', 'Converted'),
        ('closed', 'Closed'),
    )
    SOURCE_CHOICES = (
        ('quote_request', 'Quote Request'),
        ('appointment', 'Appointment'),
        ('contact_form', 'Contact Form'),
    )

    full_name = models.CharField(max_length=150)
    email = models.EmailField()
    phone = models.CharField(max_length=30, blank=True)
    company_name = models.CharField(max_length=200, blank=True)
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES, default='contact_form')
    subject = models.CharField(max_length=200, blank=True)
    message = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='new')
    assigned_laboratory = models.ForeignKey(Laboratory, related_name='contact_inquiries', on_delete=models.SET_NULL, null=True, blank=True)
    assigned_to = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='assigned_inquiries', on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    responded_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.full_name} - {self.subject or self.get_source_display()}"


class LeadResponse(models.Model):
    inquiry = models.ForeignKey(ContactInquiry, related_name='responses', on_delete=models.CASCADE)
    responder = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='lead_responses', on_delete=models.SET_NULL, null=True, blank=True)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"Response for {self.inquiry.full_name}"
