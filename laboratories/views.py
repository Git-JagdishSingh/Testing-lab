import uuid
from datetime import date, timedelta

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.views import LoginView
from django.core.mail import send_mail
from django.db.models import Count, Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.views.generic import CreateView, DeleteView, DetailView, ListView, TemplateView, UpdateView
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from rest_framework import generics, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from .forms import AdminUserForm, AppointmentForm, DetailedQuoteRequestForm, LaboratoryForm, QuotationRequestForm, QuoteMessageForm, QuoteResponseForm, ReviewForm, UserRegistrationForm
from .models import AccreditationCertificate, Appointment, Category, ComplianceReminder, ContactInquiry, FavoriteLaboratory, Laboratory, LeadResponse, QuotationRequest, QuoteMessage, Review, TestReport, User
from .rbac import AdminLeadAccessMixin, CompanyUserRequiredMixin, LabAdminRequiredMixin, SuperAdminRequiredMixin
from .serializers import CategorySerializer, LaboratorySerializer, ReviewSerializer


def logout_view(request):
    logout(request)
    return redirect('home')


class SuperAdminDashboardView(SuperAdminRequiredMixin, TemplateView):
    template_name = 'dashboards/super_admin_dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['user_count'] = User.objects.count()
        context['laboratory_count'] = Laboratory.objects.count()
        context['approved_laboratory_count'] = Laboratory.objects.filter(is_approved=True).count()
        context['appointment_count'] = Appointment.objects.count()
        context['quotation_count'] = QuotationRequest.objects.count()
        context['featured_lab_count'] = Laboratory.objects.filter(is_approved=True).count()
        context['revenue_summary'] = {
            'appointments': Appointment.objects.count(),
            'quotes': QuotationRequest.objects.count(),
        }
        return context


class LabAdminDashboardView(LabAdminRequiredMixin, TemplateView):
    template_name = 'dashboards/lab_admin_dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        labs = Laboratory.objects.filter(owner=self.request.user).select_related('owner')
        context['labs'] = labs
        context['lab_count'] = labs.count()
        context['appointment_count'] = Appointment.objects.filter(laboratory__owner=self.request.user).count()
        context['quotation_count'] = QuotationRequest.objects.filter(laboratory__owner=self.request.user).count()
        context['pending_appointments'] = Appointment.objects.filter(laboratory__owner=self.request.user, status='pending').order_by('appointment_date')[:5]
        context['recent_appointments'] = Appointment.objects.filter(laboratory__owner=self.request.user).order_by('-created_at')[:5]
        return context


class LeadManagementDashboardView(AdminLeadAccessMixin, TemplateView):
    template_name = 'dashboards/lead_management_dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.user.is_super_admin:
            labs = Laboratory.objects.all()
            quote_requests = QuotationRequest.objects.select_related('requested_by', 'laboratory').all()
            appointments = Appointment.objects.select_related('laboratory').all()
            inquiries = ContactInquiry.objects.select_related('assigned_laboratory', 'assigned_to').all()
        else:
            labs = Laboratory.objects.filter(owner=self.request.user)
            quote_requests = QuotationRequest.objects.select_related('requested_by', 'laboratory').filter(laboratory__owner=self.request.user)
            appointments = Appointment.objects.select_related('laboratory').filter(laboratory__owner=self.request.user)
            inquiries = ContactInquiry.objects.select_related('assigned_laboratory', 'assigned_to').filter(assigned_laboratory__owner=self.request.user)

        lead_rows = []
        for item in quote_requests:
            lead_rows.append({
                'type': 'Quote request',
                'title': item.subject,
                'contact': item.requested_by.get_full_name() or item.requested_by.username,
                'email': item.requested_by.email,
                'assigned_lab': item.laboratory,
                'status': item.get_status_display(),
                'created_at': item.created_at,
                'history': [],
                'source': 'quote_request',
            })
        for item in appointments:
            lead_rows.append({
                'type': 'Appointment',
                'title': f"Appointment for {item.laboratory.name}",
                'contact': item.full_name,
                'email': item.email_address,
                'assigned_lab': item.laboratory,
                'status': item.get_status_display(),
                'created_at': item.created_at,
                'history': [],
                'source': 'appointment',
            })
        for item in inquiries:
            lead_rows.append({
                'type': 'Contact inquiry',
                'title': item.subject or 'Contact inquiry',
                'contact': item.full_name,
                'email': item.email,
                'assigned_lab': item.assigned_laboratory,
                'status': item.get_status_display(),
                'created_at': item.created_at,
                'history': item.responses.all(),
                'source': item.source,
            })

        lead_rows.sort(key=lambda row: row['created_at'], reverse=True)

        converted_leads = sum(1 for row in lead_rows if row['status'].lower() in {'converted', 'quoted', 'completed', 'qualified'})
        open_leads = sum(1 for row in lead_rows if row['status'].lower() not in {'converted', 'closed'})
        conversion_rate = round((converted_leads / len(lead_rows) * 100), 1) if lead_rows else 0

        context['labs'] = labs
        context['lead_rows'] = lead_rows
        context['lead_count'] = len(lead_rows)
        context['converted_leads'] = converted_leads
        context['open_leads'] = open_leads
        context['conversion_rate'] = conversion_rate
        context['quote_request_count'] = quote_requests.count()
        context['appointment_count'] = appointments.count()
        context['inquiry_count'] = inquiries.count()
        return context


class SuperAdminLabsView(SuperAdminRequiredMixin, ListView):
    model = Laboratory
    template_name = 'super_admin/labs.html'
    context_object_name = 'labs'
    paginate_by = 10

    def get_queryset(self):
        queryset = Laboratory.objects.select_related('owner').prefetch_related('categories').order_by('-created_at')
        query = self.request.GET.get('q', '').strip()
        if query:
            queryset = queryset.filter(Q(name__icontains=query) | Q(city__icontains=query) | Q(state__icontains=query) | Q(email__icontains=query))
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['query'] = self.request.GET.get('q', '').strip()
        return context


class SuperAdminCompaniesView(SuperAdminRequiredMixin, ListView):
    model = User
    template_name = 'super_admin/companies.html'
    context_object_name = 'companies'
    paginate_by = 10

    def get_queryset(self):
        queryset = User.objects.filter(role='company_user').order_by('-date_joined')
        query = self.request.GET.get('q', '').strip()
        if query:
            queryset = queryset.filter(Q(username__icontains=query) | Q(name__icontains=query) | Q(email__icontains=query))
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['query'] = self.request.GET.get('q', '').strip()
        return context


class SuperAdminReportsView(SuperAdminRequiredMixin, ListView):
    model = TestReport
    template_name = 'super_admin/reports.html'
    context_object_name = 'reports'
    paginate_by = 10

    def get_queryset(self):
        queryset = TestReport.objects.select_related('laboratory', 'appointment', 'uploaded_by').order_by('-uploaded_at')
        query = self.request.GET.get('q', '').strip()
        if query:
            queryset = queryset.filter(Q(title__icontains=query) | Q(laboratory__name__icontains=query))
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['query'] = self.request.GET.get('q', '').strip()
        return context


class SuperAdminUsersView(SuperAdminRequiredMixin, ListView):
    model = User
    template_name = 'super_admin/users.html'
    context_object_name = 'users'
    paginate_by = 10

    def get_queryset(self):
        queryset = User.objects.exclude(is_superuser=True).order_by('-date_joined')
        query = self.request.GET.get('q', '').strip()
        if query:
            queryset = queryset.filter(Q(username__icontains=query) | Q(name__icontains=query) | Q(email__icontains=query))
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['query'] = self.request.GET.get('q', '').strip()
        return context


class SuperAdminUserUpdateView(SuperAdminRequiredMixin, UpdateView):
    model = User
    form_class = AdminUserForm
    template_name = 'super_admin/user_form.html'
    context_object_name = 'user_obj'

    def form_valid(self, form):
        messages.success(self.request, 'User profile updated successfully.')
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('super-admin-users')


class SuperAdminAnalyticsView(SuperAdminRequiredMixin, TemplateView):
    template_name = 'super_admin/analytics.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        labs = Laboratory.objects.all()
        companies = User.objects.filter(role='company_user')
        appointments = Appointment.objects.select_related('laboratory')
        quotes = QuotationRequest.objects.select_related('requested_by', 'laboratory')
        reports = TestReport.objects.select_related('laboratory')

        context['lab_count'] = labs.count()
        context['company_count'] = companies.count()
        context['appointment_count'] = appointments.count()
        context['quote_count'] = quotes.count()
        context['report_count'] = reports.count()
        context['approved_labs'] = labs.filter(is_approved=True).count()
        context['pending_labs'] = labs.filter(is_approved=False).count()
        context['appointments_by_status'] = appointments.values('status').annotate(count=Count('id')).order_by('status')
        context['recent_appointments'] = appointments.order_by('-created_at')[:6]
        context['top_labs'] = labs.order_by('-created_at')[:5]
        context['recent_companies'] = companies.order_by('-date_joined')[:5]
        return context


class HomeView(TemplateView):
    template_name = 'home.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['featured_labs'] = Laboratory.objects.filter(is_approved=True).order_by('-created_at')[:6]
        context['categories'] = Category.objects.all()[:8]
        return context


class LaboratoryListView(ListView):
    model = Laboratory
    template_name = 'laboratories/laboratory_list.html'
    context_object_name = 'labs'
    paginate_by = 6

    def get_queryset(self):
        queryset = Laboratory.objects.filter(is_approved=True).select_related('owner').prefetch_related('categories')
        query = self.request.GET.get('q', '').strip()
        city = self.request.GET.get('city', '').strip()
        state = self.request.GET.get('state', '').strip()
        category = self.request.GET.get('category', '').strip()
        rating = self.request.GET.get('rating', '').strip()

        if query:
            queryset = queryset.filter(Q(name__icontains=query) | Q(description__icontains=query) | Q(city__icontains=query))
        if city:
            queryset = queryset.filter(city__icontains=city)
        if state:
            queryset = queryset.filter(state__icontains=state)
        if category:
            queryset = queryset.filter(categories__category_name__icontains=category)
        if rating:
            queryset = queryset.filter(reviews__rating__gte=int(rating)).distinct()
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = Category.objects.all()
        return context


class LaboratoryDetailView(DetailView):
    model = Laboratory
    template_name = 'laboratories/laboratory_detail.html'
    context_object_name = 'lab'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['reviews'] = self.object.reviews.select_related('user').order_by('-created_at')
        context['appointment_form'] = AppointmentForm()
        context['certificates'] = self.object.certificates.all()
        return context


class AppointmentCreateView(CreateView):
    model = Appointment
    form_class = AppointmentForm
    template_name = 'laboratories/laboratory_detail.html'

    def dispatch(self, request, *args, **kwargs):
        self.laboratory = get_object_or_404(Laboratory, slug=self.kwargs['slug'])
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.laboratory = self.laboratory
        self.object = form.save()
        messages.success(self.request, 'Your appointment request has been submitted successfully.')
        return redirect('appointment-confirmation', slug=self.laboratory.slug, pk=self.object.pk)

    def form_invalid(self, form):
        messages.error(self.request, 'Please correct the appointment form errors and try again.')
        return redirect(self.laboratory.get_absolute_url())


class AppointmentConfirmationView(DetailView):
    model = Appointment
    template_name = 'laboratories/appointment_confirmation.html'
    context_object_name = 'appointment'

    def get_object(self, queryset=None):
        return get_object_or_404(
            Appointment.objects.select_related('laboratory'),
            pk=self.kwargs['pk'],
            laboratory__slug=self.kwargs['slug'],
        )


class AppointmentListView(LabAdminRequiredMixin, ListView):
    model = Appointment
    template_name = 'laboratories/appointment_list.html'
    context_object_name = 'appointments'
    paginate_by = 20

    def get_queryset(self):
        queryset = Appointment.objects.select_related('laboratory')
        if not self.request.user.is_super_admin:
            queryset = queryset.filter(laboratory__owner=self.request.user)
        return queryset.order_by('-appointment_date', '-created_at')


class QuoteAccessMixin(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        if self.request.user.is_super_admin or self.request.user.is_lab_admin:
            return True
        return self.request.user.is_company_user

    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            return super().handle_no_permission()
        messages.error(self.request, 'Please sign in with a company or laboratory account to access quote requests.')
        return redirect('home')


class QuoteAccessMixin(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        if self.request.user.is_super_admin or self.request.user.is_lab_admin:
            return True
        return self.request.user.is_company_user

    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            return super().handle_no_permission()
        messages.error(self.request, 'Please sign in with a company or laboratory account to access quote requests.')
        return redirect('home')


class RequestQuoteView(CompanyUserRequiredMixin, TemplateView):
    template_name = 'laboratories/request_quote.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = DetailedQuoteRequestForm()
        context['labs'] = Laboratory.objects.filter(is_approved=True).order_by('name')
        return context

    def post(self, request, *args, **kwargs):
        form = DetailedQuoteRequestForm(request.POST)
        if form.is_valid():
            quote_request = form.save(commit=False)
            quote_request.requested_by = request.user
            quote_request.company_name = quote_request.company_name or request.user.name or request.user.username
            quote_request.contact_name = quote_request.contact_name or request.user.get_full_name() or request.user.username
            quote_request.contact_email = quote_request.contact_email or request.user.email
            quote_request.status = 'pending'
            quote_request.save()
            messages.success(request, 'Your quote request has been submitted and is awaiting a response.')
            return redirect('request-quote')

        messages.error(request, 'Please correct the quote request form errors and try again.')
        return self.render_to_response(self.get_context_data(form=form))


class QuoteRequestListView(QuoteAccessMixin, ListView):
    model = QuotationRequest
    template_name = 'laboratories/quote_request_list.html'
    context_object_name = 'quote_requests'
    paginate_by = 20

    def get_queryset(self):
        queryset = QuotationRequest.objects.select_related('requested_by', 'laboratory').order_by('-created_at')
        if self.request.user.is_company_user and not self.request.user.is_super_admin:
            queryset = queryset.filter(requested_by=self.request.user)
        elif not self.request.user.is_super_admin:
            queryset = queryset.filter(Q(laboratory__owner=self.request.user) | Q(laboratory__isnull=True))
        return queryset


class QuoteConversationView(QuoteAccessMixin, TemplateView):
    template_name = 'laboratories/quote_conversation.html'

    def dispatch(self, request, *args, **kwargs):
        self.quote_request = get_object_or_404(QuotationRequest.objects.select_related('requested_by', 'laboratory'), pk=self.kwargs['pk'])
        if request.user.is_company_user and self.quote_request.requested_by_id != request.user.id:
            messages.error(request, 'You can only view your own quote requests.')
            return redirect('quote-list')
        if not request.user.is_super_admin and request.user.is_lab_admin and self.quote_request.laboratory and self.quote_request.laboratory.owner_id != request.user.id:
            messages.error(request, 'You can only view requests for your laboratories.')
            return redirect('quote-list')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        self.quote_request.mark_messages_read_for(self.request.user)
        context['quote_request'] = self.quote_request
        context['messages'] = self.quote_request.messages.select_related('sender', 'recipient').all()
        context['form'] = kwargs.get('form') or QuoteMessageForm()
        return context

    def post(self, request, *args, **kwargs):
        form = QuoteMessageForm(request.POST)
        if form.is_valid():
            message = form.save(commit=False)
            message.quote_request = self.quote_request
            message.sender = request.user
            message.recipient = self.quote_request.laboratory.owner if request.user.is_company_user else self.quote_request.requested_by
            message.is_read = False
            message.save()
            self.quote_request.status = 'received' if message.message_type == 'quotation' else self.quote_request.status
            self.quote_request.save(update_fields=['status', 'updated_at'])
            if message.recipient and message.recipient.email:
                send_mail(
                    f'New quote update from {request.user.get_full_name() or request.user.username}',
                    f"A new {message.get_message_type_display().lower()} was added to your quote request for {self.quote_request.test_type or self.quote_request.subject}.\n\n{message.message}",
                    settings.DEFAULT_FROM_EMAIL,
                    [message.recipient.email],
                    fail_silently=True,
                )
            messages.success(request, 'Your message has been sent.')
            return redirect('quote-conversation', pk=self.quote_request.pk)

        messages.error(request, 'Please enter a message before submitting it.')
        return self.render_to_response(self.get_context_data(form=form))


class QuoteResponseView(AdminLeadAccessMixin, TemplateView):
    template_name = 'laboratories/quote_response_form.html'

    def dispatch(self, request, *args, **kwargs):
        self.quote_request = get_object_or_404(
            QuotationRequest.objects.select_related('requested_by', 'laboratory'),
            pk=self.kwargs['pk'],
        )
        if not request.user.is_super_admin and not (self.quote_request.laboratory and self.quote_request.laboratory.owner == request.user):
            messages.error(request, 'You can only respond to requests for your own laboratory.')
            return redirect('quote-list')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['quote_request'] = self.quote_request
        context['form'] = kwargs.get('form') or QuoteResponseForm(instance=self.quote_request)
        return context

    def post(self, request, *args, **kwargs):
        form = QuoteResponseForm(request.POST, instance=self.quote_request)
        if form.is_valid():
            quote_request = form.save(commit=False)
            if quote_request.status in {'received', 'accepted', 'rejected'} and not quote_request.responded_at:
                quote_request.responded_at = timezone.now()
            elif quote_request.status == 'pending':
                quote_request.responded_at = None
            quote_request.save()
            messages.success(request, 'The quotation response has been saved.')
            return redirect('quote-list')

        messages.error(request, 'Please correct the quotation response form errors and try again.')
        return self.render_to_response(self.get_context_data(form=form))


class CompanyPortalView(CompanyUserRequiredMixin, TemplateView):
    template_name = 'company_portal.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        company_labs = Laboratory.objects.filter(owner=self.request.user).order_by('-created_at')[:6]
        reminders = ComplianceReminder.objects.filter(requested_by=self.request.user).order_by('due_date')
        if not reminders.exists():
            for lab in company_labs:
                reminders.create(
                    requested_by=self.request.user,
                    laboratory=lab,
                    title=f'Review compliance renewal for {lab.name}',
                    due_date=date.today() + timedelta(days=45),
                    description='Plan your next renewal review before the due date.',
                )
            reminders = ComplianceReminder.objects.filter(requested_by=self.request.user).order_by('due_date')

        context['company_labs'] = company_labs
        context['available_laboratories'] = Laboratory.objects.filter(is_approved=True).exclude(owner=self.request.user).order_by('name')[:12]
        context['appointments'] = Appointment.objects.filter(laboratory__owner=self.request.user).select_related('laboratory').order_by('-appointment_date', '-created_at')[:10]
        context['favorite_labs'] = FavoriteLaboratory.objects.filter(user=self.request.user).select_related('laboratory')[:8]
        context['quotation_form'] = QuotationRequestForm()
        context['quotation_requests'] = QuotationRequest.objects.filter(requested_by=self.request.user).order_by('-created_at')[:5]
        context['reminders'] = reminders[:5]
        return context

    def post(self, request, *args, **kwargs):
        action = request.POST.get('action')
        if action == 'favorite-toggle':
            laboratory_slug = request.POST.get('laboratory_slug')
            laboratory = get_object_or_404(Laboratory, slug=laboratory_slug)
            favorite = FavoriteLaboratory.objects.filter(user=request.user, laboratory=laboratory).first()
            if favorite:
                favorite.delete()
                messages.success(request, 'Removed the laboratory from your favorites.')
            else:
                FavoriteLaboratory.objects.create(user=request.user, laboratory=laboratory)
                messages.success(request, 'Added the laboratory to your favorites.')
            return redirect('company-portal')

        if action == 'quotation-request':
            form = QuotationRequestForm(request.POST)
            if form.is_valid():
                quotation = form.save(commit=False)
                quotation.requested_by = request.user
                quotation.company_name = quotation.company_name or request.user.name or request.user.username
                quotation.contact_name = quotation.contact_name or request.user.get_full_name() or request.user.username
                quotation.contact_email = quotation.contact_email or request.user.email
                quotation.status = 'pending'
                if not quotation.subject and quotation.test_type:
                    quotation.subject = f"Quote request for {quotation.test_type}"
                quotation.save()
                messages.success(request, 'Your quotation request has been submitted.')
            else:
                messages.error(request, 'Please complete the quotation request form before submitting.')
            return redirect('company-portal')

        messages.error(request, 'The requested action could not be completed.')
        return redirect('company-portal')


def company_report_download(request):
    if not request.user.is_authenticated or not request.user.is_company_user:
        messages.error(request, 'Please sign in with a company account to download this report.')
        return redirect('home')

    appointments = Appointment.objects.filter(laboratory__owner=request.user).select_related('laboratory').order_by('-appointment_date')
    favorites = FavoriteLaboratory.objects.filter(user=request.user).select_related('laboratory').order_by('-created_at')
    reminders = ComplianceReminder.objects.filter(requested_by=request.user).order_by('due_date')

    lines = [
        'Company Portal Report',
        f'Generated for: {request.user.get_full_name() or request.user.username}',
        '',
        'Appointments:',
    ]
    if appointments:
        for appointment in appointments:
            lines.append(f"- {appointment.reference_number}: {appointment.laboratory.name} on {appointment.appointment_date} ({appointment.status})")
    else:
        lines.append('- No appointments recorded yet.')

    lines.extend(['', 'Favorite Laboratories:'])
    if favorites:
        for favorite in favorites:
            lines.append(f"- {favorite.laboratory.name}")
    else:
        lines.append('- No favorite laboratories saved yet.')

    lines.extend(['', 'Compliance Reminders:'])
    if reminders:
        for reminder in reminders:
            lines.append(f"- {reminder.title} due {reminder.due_date} ({reminder.description or 'No additional note'})")
    else:
        lines.append('- No reminders scheduled yet.')

    response = HttpResponse('\n'.join(lines), content_type='text/plain; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="company_portal_report.txt"'
    return response


class LaboratoryCreateView(LabAdminRequiredMixin, CreateView):
    model = Laboratory
    form_class = LaboratoryForm
    template_name = 'laboratories/laboratory_form.html'

    def form_valid(self, form):
        form.instance.owner = self.request.user
        form.instance.is_approved = True
        response = super().form_valid(form)
        for image in self.request.FILES.getlist('accreditation_certificates'):
            AccreditationCertificate.objects.create(laboratory=self.object, image=image)
        messages.success(self.request, 'Laboratory profile created and is ready for management.')
        return response


class LaboratoryUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Laboratory
    form_class = LaboratoryForm
    template_name = 'laboratories/laboratory_form.html'

    def test_func(self):
        return self.get_object().owner == self.request.user or self.request.user.is_super_admin

    def form_valid(self, form):
        response = super().form_valid(form)
        for image in self.request.FILES.getlist('accreditation_certificates'):
            AccreditationCertificate.objects.create(laboratory=self.object, image=image)
        return response


class ReviewCreateView(LoginRequiredMixin, CreateView):
    model = Review
    form_class = ReviewForm
    template_name = 'laboratories/review_form.html'

    def form_valid(self, form):
        laboratory = get_object_or_404(Laboratory, slug=self.kwargs['slug'])
        form.instance.laboratory = laboratory
        form.instance.user = self.request.user
        messages.success(self.request, 'Your review has been submitted.')
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('laboratory-detail', kwargs={'slug': self.kwargs['slug']})


class ReviewUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Review
    form_class = ReviewForm
    template_name = 'laboratories/review_form.html'

    def test_func(self):
        return self.get_object().user == self.request.user

    def get_success_url(self):
        return reverse('laboratory-detail', kwargs={'slug': self.object.laboratory.slug})


class ReviewDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = Review
    template_name = 'laboratories/review_confirm_delete.html'

    def test_func(self):
        return self.get_object().user == self.request.user

    def get_success_url(self):
        return reverse('laboratory-detail', kwargs={'slug': self.object.laboratory.slug})


class RegisterView(CreateView):
    model = User
    form_class = UserRegistrationForm
    template_name = 'registration/register.html'

    def form_valid(self, form):
        user = form.save(commit=False)
        user.is_active = False
        user.is_verified = False
        user.verification_token = uuid.uuid4().hex
        user.save()
        verification_link = self.request.build_absolute_uri(reverse('verify-email', kwargs={'token': user.verification_token}))
        send_mail(
            'Verify your TestLab Finder account',
            f'Please verify your account by visiting: {verification_link}',
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            fail_silently=False,
        )
        messages.success(self.request, 'Your account has been created. Please verify your email.')
        return redirect('verification-sent')


class VerificationSentView(TemplateView):
    template_name = 'registration/verification_sent.html'


class VerifyEmailView(TemplateView):
    template_name = 'registration/verification_complete.html'

    def get(self, request, token):
        user = get_object_or_404(User, verification_token=token)
        user.is_active = True
        user.is_verified = True
        user.verification_token = ''
        user.save(update_fields=['is_active', 'is_verified', 'verification_token'])
        messages.success(request, 'Your email has been verified. You can now log in.')
        return redirect('login')


class LoginView(LoginView):
    template_name = 'registration/login.html'


class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer


class LaboratoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Laboratory.objects.filter(is_approved=True)
    serializer_class = LaboratorySerializer
    lookup_field = 'slug'


class ReviewViewSet(viewsets.ModelViewSet):
    queryset = Review.objects.all()
    serializer_class = ReviewSerializer

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class SearchAPIView(APIView):
    def get(self, request):
        query = request.query_params.get('q', '').strip()
        labs = Laboratory.objects.filter(is_approved=True)
        if query:
            labs = labs.filter(Q(name__icontains=query) | Q(city__icontains=query) | Q(state__icontains=query))
        serializer = LaboratorySerializer(labs[:10], many=True)
        return Response(serializer.data)
