from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import redirect


class RoleRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    allowed_roles = ()
    error_message = 'You do not have permission to access this area.'
    redirect_url = 'home'

    def test_func(self):
        if not self.request.user.is_authenticated:
            return False
        if self.request.user.is_super_admin:
            return True
        return self.request.user.normalized_role in self.allowed_roles

    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            return super().handle_no_permission()
        messages.error(self.request, self.error_message)
        return redirect(self.redirect_url)


class SuperAdminRequiredMixin(RoleRequiredMixin):
    allowed_roles = ('super_admin',)
    error_message = 'Only super administrators can access this dashboard.'


class LabAdminRequiredMixin(RoleRequiredMixin):
    allowed_roles = ('lab_admin',)
    error_message = 'Only lab administrators can access this dashboard.'


class CompanyUserRequiredMixin(RoleRequiredMixin):
    allowed_roles = ('company_user',)
    error_message = 'Please sign in with a company account to access this portal.'


class AdminLeadAccessMixin(RoleRequiredMixin):
    allowed_roles = ('super_admin', 'lab_admin')
    error_message = 'Only administrators and lab managers can access lead management.'
