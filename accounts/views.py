from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.views import LoginView
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse_lazy
from .forms import UserRegistrationForm, UserProfileForm

class CustomLoginView(LoginView):
    template_name = 'accounts/login.html'
    redirect_authenticated_user = True

    def get_success_url(self):
        messages.success(self.request, f"Welcome back, {self.request.user.username}!")
        if hasattr(self.request.user, 'profile') and self.request.user.profile.is_authority:
            return reverse_lazy('dashboard:home')
        return reverse_lazy('reports:list')


def register_view(request):
    if request.user.is_authenticated:
        if hasattr(request.user, 'profile') and request.user.profile.is_authority:
            return redirect('dashboard:home')
        return redirect('reports:list')
    
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f"Account successfully created! Logged in as {user.username}.")
            if hasattr(user, 'profile') and user.profile.is_authority:
                return redirect('dashboard:home')
            return redirect('reports:list')
        else:
            messages.error(request, "Please correct the registration errors below.")
    else:
        form = UserRegistrationForm()
        
    return render(request, 'accounts/register.html', {'form': form})



from django.views.decorators.cache import never_cache

@never_cache
def logout_view(request):
    logout(request)
    if hasattr(request, 'session'):
        request.session.flush()
    messages.info(request, "You have been successfully logged out.")
    return redirect('dashboard:home')



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
        form = UserProfileForm(instance=profile)
        
    return render(request, 'accounts/profile.html', {
        'form': form,
        'profile': profile
    })
