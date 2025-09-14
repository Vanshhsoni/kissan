from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate
from .models import User
from .forms import UserRegisterForm

def auth_view(request):
    if request.method == "POST":
        mobile = request.POST.get("mobile")
        if not mobile:
            return render(request, "accounts/auth.html", {"error": "Mobile number is required"})
        
        try:
            # User exists, authenticate and log them in
            user = User.objects.get(mobile=mobile)
            # Set backend attribute
            user.backend = 'accounts.backends.MobileBackend'
            login(request, user)
            return redirect("dashboard")
        except User.DoesNotExist:
            # User doesn't exist, redirect to registration with mobile number
            return redirect(f"/accounts/register/?mobile={mobile}")
    
    return render(request, "accounts/auth.html")


def register_view(request):
    # Get mobile number from URL parameter (for new users)
    mobile_from_auth = request.GET.get("mobile")
    
    if request.method == "POST":
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Set backend attribute
            user.backend = 'accounts.backends.MobileBackend'
            login(request, user)
            return redirect("dashboard")
        else:
            print("Form errors:", form.errors)
            return render(request, "accounts/register.html", {
                "form": form, 
                "mobile_from_auth": mobile_from_auth
            })
    else:
        # Pre-fill form with mobile number if coming from auth
        initial_data = {}
        if mobile_from_auth:
            initial_data["mobile"] = mobile_from_auth
        
        form = UserRegisterForm(initial=initial_data)
    
    return render(request, "accounts/register.html", {
        "form": form, 
        "mobile_from_auth": mobile_from_auth
    })