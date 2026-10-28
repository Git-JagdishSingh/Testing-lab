from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from .models import Appointment, FavoriteLaboratory, Laboratory, QuotationRequest, QuoteMessage, Review, User


class LaboratoryModelTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username='owner', password='secret123', email='owner@example.com')

    def test_average_rating_is_zero_for_laboratory_without_reviews(self):
        lab = Laboratory.objects.create(
            owner=self.owner,
            name="Alpha Labs",
            description="Quality testing lab",
            city="Mumbai",
            state="Maharashtra",
            address="123 Main Street",
            phone="9876543210",
            email="contact@alphalabs.com",
            accreditation="ISO 17025",
            is_approved=True,
        )

        self.assertEqual(lab.average_rating, 0)

    def test_average_rating_uses_review_scores(self):
        lab = Laboratory.objects.create(
            owner=self.owner,
            name="Beta Labs",
            description="Testing lab",
            city="Delhi",
            state="Delhi",
            address="456 Market Road",
            phone="9123456780",
            email="info@betalabs.com",
            accreditation="NABL",
            is_approved=True,
        )
        Review.objects.create(laboratory=lab, user=self.owner, rating=5, review_text="Excellent")
        Review.objects.create(laboratory=lab, user=self.owner, rating=3, review_text="Good")

        self.assertEqual(lab.average_rating, 4.0)


class AppointmentBookingTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username='owner', password='secret123', email='owner@example.com')
        self.lab = Laboratory.objects.create(
            owner=self.owner,
            name='Precision Labs',
            description='A modern lab for testing',
            city='Bengaluru',
            state='Karnataka',
            address='1st Main Road',
            phone='9876543210',
            email='info@precisionlabs.com',
            accreditation='ISO 17025',
            is_approved=True,
        )

    def test_guest_user_can_book_appointment_and_see_confirmation(self):
        response = self.client.post(
            reverse('appointment-create', kwargs={'slug': self.lab.slug}),
            {
                'full_name': 'Jane Doe',
                'contact_number': '9988776655',
                'email_address': 'jane@example.com',
                'appointment_date': '2030-01-15',
            },
        )

        self.assertEqual(response.status_code, 302)
        appointment = Appointment.objects.get(full_name='Jane Doe')
        self.assertRedirects(response, reverse('appointment-confirmation', kwargs={'slug': self.lab.slug, 'pk': appointment.pk}))

        confirmation_response = self.client.get(response.url)
        self.assertContains(confirmation_response, 'Your appointment has been booked successfully')
        self.assertContains(confirmation_response, appointment.reference_number)
        self.assertContains(confirmation_response, appointment.full_name)
        self.assertContains(confirmation_response, self.lab.name)
        self.assertContains(confirmation_response, 'Register')
        self.assertContains(confirmation_response, 'Login')

    def test_appointment_history_requires_login(self):
        response = self.client.get(reverse('appointment-list'))

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('login'), response.url)


class CompanyPortalTests(TestCase):
    def setUp(self):
        self.company = User.objects.create_user(
            username='companyuser',
            password='secret123',
            email='company@example.com',
            role='company_user',
        )
        self.lab = Laboratory.objects.create(
            owner=self.company,
            name='Northwind Labs',
            description='Reliable testing services',
            city='Mumbai',
            state='Maharashtra',
            address='7th Avenue',
            phone='9898989898',
            email='northwind@example.com',
            accreditation='ISO 17025',
            is_approved=True,
        )

    def test_company_user_can_access_portal_and_save_favorite_lab(self):
        self.client.force_login(self.company)

        response = self.client.get(reverse('company-portal'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Company Portal')

        favorite_response = self.client.post(
            reverse('company-portal'),
            {'action': 'favorite-toggle', 'laboratory_slug': self.lab.slug},
        )
        self.assertEqual(favorite_response.status_code, 302)
        self.assertTrue(FavoriteLaboratory.objects.filter(user=self.company, laboratory=self.lab).exists())

    def test_company_user_can_submit_a_quotation_request(self):
        self.client.force_login(self.company)

        response = self.client.post(
            reverse('company-portal'),
            {
                'action': 'quotation-request',
                'laboratory': self.lab.pk,
                'subject': 'Need a quotation',
                'message': 'Please share testing pricing for the next quarter.',
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(QuotationRequest.objects.filter(requested_by=self.company, subject='Need a quotation').exists())


class QuoteRequestTests(TestCase):
    def setUp(self):
        self.company = User.objects.create_user(
            username='companyuser3',
            password='secret123',
            email='company3@example.com',
            role='company_user',
        )
        self.lab_owner = User.objects.create_user(
            username='labowner2',
            password='secret123',
            email='labowner2@example.com',
            role='lab_admin',
        )
        self.lab = Laboratory.objects.create(
            owner=self.lab_owner,
            name='Nova Testing Labs',
            description='Advanced testing services',
            city='Pune',
            state='Maharashtra',
            address='88 Market Street',
            phone='9899999999',
            email='nova@example.com',
            accreditation='NABL',
            is_approved=True,
        )

    def test_company_user_can_submit_a_detailed_quote_request(self):
        self.client.force_login(self.company)

        response = self.client.post(
            reverse('request-quote'),
            {
                'laboratory': self.lab.pk,
                'test_type': 'Microbial testing',
                'product_or_sample_details': '3 sample bottles',
                'company_name': 'Bright Industries',
                'contact_name': 'Nina Patel',
                'contact_email': 'nina@bright.com',
                'contact_phone': '9988776655',
                'location': 'Pune',
                'preferred_timeline': 'Within 2 weeks',
                'message': 'We need a fast turnaround for a new product line.',
            },
        )

        self.assertEqual(response.status_code, 302)
        quote_request = QuotationRequest.objects.get(contact_name='Nina Patel')
        self.assertEqual(quote_request.status, 'pending')
        self.assertEqual(quote_request.test_type, 'Microbial testing')
        self.assertEqual(quote_request.location, 'Pune')

    def test_lab_admin_can_respond_to_quote_request_and_update_status(self):
        quote_request = QuotationRequest.objects.create(
            requested_by=self.company,
            laboratory=self.lab,
            test_type='Chemical analysis',
            product_or_sample_details='5 kg sample',
            company_name='Bright Industries',
            contact_name='Nina Patel',
            contact_email='nina@bright.com',
            contact_phone='9988776655',
            location='Pune',
            preferred_timeline='Within 3 weeks',
            message='Please share a quote.',
            status='pending',
        )

        self.client.force_login(self.lab_owner)
        response = self.client.post(
            reverse('quote-response', kwargs={'pk': quote_request.pk}),
            {
                'quote_amount': '1500.00',
                'lab_response': 'We can complete this within 2 weeks.',
                'status': 'received',
            },
        )

        self.assertEqual(response.status_code, 302)
        quote_request.refresh_from_db()
        self.assertEqual(quote_request.status, 'received')
        self.assertEqual(quote_request.quote_amount, Decimal('1500.00'))
        self.assertEqual(quote_request.lab_response, 'We can complete this within 2 weeks.')


class QuoteConversationTests(TestCase):
    def setUp(self):
        self.company = User.objects.create_user(
            username='companyuser4',
            password='secret123',
            email='company4@example.com',
            role='company_user',
        )
        self.lab_owner = User.objects.create_user(
            username='labowner3',
            password='secret123',
            email='labowner3@example.com',
            role='lab_admin',
        )
        self.lab = Laboratory.objects.create(
            owner=self.lab_owner,
            name='Summit Labs',
            description='Precision testing services',
            city='Mumbai',
            state='Maharashtra',
            address='42 Market Road',
            phone='9900000000',
            email='summit@example.com',
            accreditation='ISO 17025',
            is_approved=True,
        )
        self.quote_request = QuotationRequest.objects.create(
            requested_by=self.company,
            laboratory=self.lab,
            test_type='Sterility testing',
            product_or_sample_details='2 sealed vials',
            company_name='Evergreen Co',
            contact_name='Rina Shah',
            contact_email='rina@evergreen.com',
            contact_phone='9090909090',
            location='Mumbai',
            preferred_timeline='Within 1 week',
            message='Please share quote details.',
            status='pending',
        )

    def test_lab_message_and_user_reply_are_recorded_in_conversation(self):
        self.client.force_login(self.lab_owner)
        response = self.client.post(
            reverse('quote-conversation', kwargs={'pk': self.quote_request.pk}),
            {
                'message': 'We can support this request. Please share the batch size.',
                'message_type': 'message',
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(QuoteMessage.objects.filter(quote_request=self.quote_request, sender=self.lab_owner).exists())

        self.client.force_login(self.company)
        reply_response = self.client.post(
            reverse('quote-conversation', kwargs={'pk': self.quote_request.pk}),
            {
                'message': 'We will provide the batch size shortly.',
                'message_type': 'message',
            },
        )
        self.assertEqual(reply_response.status_code, 302)
        self.assertEqual(self.quote_request.get_unread_count_for(self.lab_owner), 1)


class RoleBasedAccessTests(TestCase):
    def setUp(self):
        self.super_admin = User.objects.create_user(
            username='superadmin',
            password='secret123',
            email='super@example.com',
            role='super_admin',
        )
        self.lab_admin = User.objects.create_user(
            username='labadmin',
            password='secret123',
            email='lab@example.com',
            role='lab_admin',
        )
        self.company_user = User.objects.create_user(
            username='companyuser2',
            password='secret123',
            email='company2@example.com',
            role='company_user',
        )

    def test_role_helpers_and_dashboards_are_available_for_each_role(self):
        self.assertTrue(self.super_admin.is_super_admin)
        self.assertTrue(self.lab_admin.is_lab_admin)
        self.assertTrue(self.company_user.is_company_user)

        self.client.force_login(self.super_admin)
        response = self.client.get(reverse('super-admin-dashboard'))
        self.assertEqual(response.status_code, 200)

        self.client.force_login(self.lab_admin)
        response = self.client.get(reverse('lab-admin-dashboard'))
        self.assertEqual(response.status_code, 200)

        self.client.force_login(self.company_user)
        response = self.client.get(reverse('company-portal'))
        self.assertEqual(response.status_code, 200)

    def test_non_super_admin_users_are_blocked_from_super_admin_dashboard(self):
        self.client.force_login(self.lab_admin)
        response = self.client.get(reverse('super-admin-dashboard'))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('home'))

    def test_admin_roles_can_access_lead_management_dashboard(self):
        self.client.force_login(self.super_admin)
        response = self.client.get(reverse('lead-management-dashboard'))
        self.assertEqual(response.status_code, 200)

        self.client.force_login(self.lab_admin)
        response = self.client.get(reverse('lead-management-dashboard'))
        self.assertEqual(response.status_code, 200)

    def test_super_admin_can_access_core_admin_pages(self):
        self.client.force_login(self.super_admin)
        for name in [
            'super-admin-labs',
            'super-admin-companies',
            'super-admin-reports',
            'super-admin-users',
            'super-admin-analytics',
        ]:
            response = self.client.get(reverse(name))
            self.assertEqual(response.status_code, 200, msg=f'{name} should load for super admin')
