from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.views import LoginView
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse
from django.views.decorators.cache import never_cache
import logging

from .forms import UserRegistrationForm, UserProfileForm, CustomAuthenticationForm

logger = logging.getLogger(__name__)


def get_role_landing(user):
    """Module landing page per account type.

    - Admin   -> Django admin site (platform configuration)
    - Ranger  -> Forest/ranger dashboard (falls back to citizen module for now;
                dedicated ranger console will be built separately)
    - Citizen -> Sightings module
    """
    if not user.is_authenticated:
        return reverse('dashboard:home')
    profile = getattr(user, 'profile', None)
    if profile is None:
        return reverse('reports:list')
    if profile.is_admin:
        return reverse('admin:index')
    # Ranger currently redirects into the citizen module until the
    # dedicated ranger console exists.
    return reverse('reports:list')


class CustomLoginView(LoginView):
    template_name = 'accounts/login.html'
    authentication_form = CustomAuthenticationForm
    redirect_authenticated_user = True

    def get_success_url(self):
        user = self.request.user
        messages.success(self.request, f"Welcome back, {user.username}! Signed in as {user.profile.get_role_display()}.")
        # Honour an explicit ?next= only when it is a safe internal URL.
        nxt = self.request.GET.get('next') or self.request.POST.get('next')
        from django.utils.http import url_has_allowed_host_and_scheme
        if nxt and url_has_allowed_host_and_scheme(nxt, allowed_hosts={self.request.get_host()}, require_secure=self.request.is_secure()):
            return nxt
        return get_role_landing(user)


@never_cache
def register_view(request):
    if request.user.is_authenticated:
        return redirect(get_role_landing(request.user))

    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f"Account created successfully! You are signed in as {user.username} ({user.profile.get_role_display()}).")
            return redirect(get_role_landing(user))
        else:
            messages.error(request, "Please correct the errors below and try again.")
    else:
        form = UserRegistrationForm()

    return render(request, 'accounts/register.html', {'form': form})


@never_cache
def logout_view(request):
    """Properly terminate the user's Django session."""
    if request.user.is_authenticated:
        logger.info(f"Logging out user: {request.user.username}")

    logout(request)

    # Flush the session to remove all session data
    if hasattr(request, 'session'):
        request.session.flush()
        logger.info("Session flushed successfully")

    messages.info(request, "You have been successfully logged out.")
    return redirect('accounts:login')


@login_required
@never_cache
def profile_view(request):
    profile = request.user.profile
    if request.method == 'POST':
        form = UserProfileForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, "Your profile details have been updated.")
            return redirect('accounts:profile')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = UserProfileForm(instance=profile)

    return render(request, 'accounts/profile.html', {
        'form': form,
        'profile': profile
    })
