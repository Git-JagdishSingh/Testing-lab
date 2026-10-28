from datetime import date

from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import Appointment, Category, Laboratory, QuotationRequest, QuoteMessage, Review, User


class AdminUserForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['username', 'name', 'email', 'role', 'is_active', 'is_verified']
        widgets = {
            'role': forms.Select(choices=User.ROLE_CHOICES),
        }


class MultiClearableFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True

    def value_from_datadict(self, data, files, name):
        if name in files:
            return files.getlist(name)
        return super().value_from_datadict(data, files, name)


class MultiFileField(forms.FileField):
    widget = MultiClearableFileInput

    def to_python(self, data):
        if data in self.empty_values:
            return None
        if isinstance(data, list):
            files = []
            for item in data:
                if item not in self.empty_values:
                    files.append(super(MultiFileField, self).to_python(item))
            return files
        return super().to_python(data)

    def validate(self, data):
        if data in self.empty_values:
            return
        if isinstance(data, list):
            for item in data:
                super().validate(item)
            return
        super().validate(data)


class UserRegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    role = forms.ChoiceField(
        choices=(
            ('company_user', 'Company User'),
            ('lab_admin', 'Lab Admin'),
        ),
        initial='company_user'
    )

    class Meta:
        model = User
        fields = ('username', 'name', 'email', 'role', 'password1', 'password2')

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.name = self.cleaned_data.get('name', '')
        user.role = self.cleaned_data['role']
        user.is_active = False
        if commit:
            user.save()
        return user


class LaboratoryForm(forms.ModelForm):
    categories = forms.ModelMultipleChoiceField(
        queryset=Category.objects.all(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
    )
    accreditation_certificates = MultiFileField(
        widget=MultiClearableFileInput(attrs={'multiple': True}),
        required=False,
        help_text='Upload JPG, JPEG, PNG, or WebP accreditation certificate images.',
    )

    class Meta:
        model = Laboratory
        fields = [
            'name',
            'description',
            'city',
            'state',
            'address',
            'phone',
            'email',
            'website',
            'accreditation',
            'accreditation_certificates',
            'categories',
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 5}),
        }


class AppointmentForm(forms.ModelForm):
    class Meta:
        model = Appointment
        fields = ['full_name', 'contact_number', 'email_address', 'appointment_date']
        widgets = {
            'appointment_date': forms.DateInput(attrs={'type': 'date'}),
        }

    def clean_appointment_date(self):
        appointment_date = self.cleaned_data.get('appointment_date')
        if appointment_date and appointment_date < date.today():
            raise forms.ValidationError('Appointment date cannot be in the past.')
        return appointment_date


class QuotationRequestForm(forms.ModelForm):
    class Meta:
        model = QuotationRequest
        fields = [
            'laboratory',
            'subject',
            'test_type',
            'product_or_sample_details',
            'company_name',
            'contact_name',
            'contact_email',
            'contact_phone',
            'location',
            'preferred_timeline',
            'message',
        ]
        widgets = {
            'product_or_sample_details': forms.Textarea(attrs={'rows': 3}),
            'message': forms.Textarea(attrs={'rows': 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['laboratory'].queryset = Laboratory.objects.filter(is_approved=True).order_by('name')
        self.fields['laboratory'].required = False
        self.fields['subject'].required = False
        self.fields['test_type'].required = False
        self.fields['product_or_sample_details'].required = False
        self.fields['company_name'].required = False
        self.fields['contact_name'].required = False
        self.fields['contact_email'].required = False
        self.fields['contact_phone'].required = False
        self.fields['location'].required = False
        self.fields['preferred_timeline'].required = False
        self.fields['message'].required = False


class DetailedQuoteRequestForm(QuotationRequestForm):
    class Meta(QuotationRequestForm.Meta):
        fields = QuotationRequestForm.Meta.fields

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['test_type'].required = True
        self.fields['product_or_sample_details'].required = True
        self.fields['company_name'].required = True
        self.fields['contact_name'].required = True
        self.fields['contact_email'].required = True
        self.fields['contact_phone'].required = True
        self.fields['location'].required = True
        self.fields['preferred_timeline'].required = True


class QuoteResponseForm(forms.ModelForm):
    class Meta:
        model = QuotationRequest
        fields = ['quote_amount', 'lab_response', 'status']
        widgets = {
            'lab_response': forms.Textarea(attrs={'rows': 4}),
        }


class QuoteMessageForm(forms.ModelForm):
    class Meta:
        model = QuoteMessage
        fields = ['message', 'message_type', 'quote_amount']
        widgets = {
            'message': forms.Textarea(attrs={'rows': 4}),
        }

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get('message_type') == 'quotation' and not cleaned_data.get('quote_amount'):
            self.add_error('quote_amount', 'A quotation amount is required when sending a quotation.')
        return cleaned_data


class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ['rating', 'review_text']
        widgets = {
            'review_text': forms.Textarea(attrs={'rows': 4}),
        }
