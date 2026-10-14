# accounts/views.py
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib.auth.decorators import login_required
from django.core.signing import TimestampSigner, BadSignature, SignatureExpired
from django.db import transaction
from django.shortcuts import render, redirect
from django.urls import reverse
from django.views.decorators.http import require_http_methods

from .forms import SignupForm, LoginForm, ResetStep1Form, SetNewPasswordForm
from .models import SecurityQuestion, UserSecurityAnswer, RecoveryCode

User = get_user_model()
signer = TimestampSigner()   # adds a timestamp + HMAC to the token


# ---------- SIGNUP ----------
@require_http_methods(["GET", "POST"])
def signup(request):
    if request.user.is_authenticated:
        return redirect("accounts:profile")

    form = SignupForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():   # all-or-nothing: if hashing fails, no half-user
            user = User.objects.create_user(
                username=form.cleaned_data["username"],
                password=form.cleaned_data["password"],
                full_name=form.cleaned_data["full_name"],
            )
            # store hashed security answer
            UserSecurityAnswer.objects.create(
                user=user,
                question=form.cleaned_data["question"],
                answer_hash=UserSecurityAnswer.hash_answer(form.cleaned_data["answer"]),
            )
            # generate recovery codes, store hashed, keep plaintext for one-time display
            pairs = RecoveryCode.generate_codes(8)
            RecoveryCode.objects.bulk_create(
                [RecoveryCode(user=user, code_hash=h) for _, h in pairs]
            )
            # stash plaintext in session so we can show them once after redirect
            request.session["new_recovery_codes"] = [c for c, _ in pairs]
            request.session["new_username"] = user.username

        login(request, user)   # auto-login after signup
        return redirect("accounts:recovery_codes")

    return render(request, "accounts/signup.html", {"form": form})


# ---------- RECOVERY CODE ONE-TIME DISPLAY ----------
@login_required
def recovery_codes(request):
    codes = request.session.pop("new_recovery_codes", None)
    return render(request, "accounts/recovery_codes.html", {"codes": codes})


# ---------- LOGIN ----------
@require_http_methods(["GET", "POST"])
def login_view(request):
    if request.user.is_authenticated:
        return redirect("accounts:profile")

    form = LoginForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = authenticate(
            request,
            username=form.cleaned_data["username"].lower(),
            password=form.cleaned_data["password"],
        )
        if user is None:
            # generic message — never reveal whether the username exists
            messages.error(request, "Invalid username or password.")
        else:
            login(request, user)
            return redirect("accounts:profile")

    return render(request, "accounts/login.html", {"form": form})


# ---------- LOGOUT ----------
def logout_view(request):
    logout(request)
    return redirect("accounts:login")


# ---------- PROFILE ----------
@login_required
def profile(request):
    return render(request, "accounts/profile.html")


# ---------- PASSWORD RESET: STEP 1 (verify identity) ----------
@require_http_methods(["GET", "POST"])
def reset_step1(request):
    form = ResetStep1Form(request.POST or None)
    if request.method == "POST" and form.is_valid():
        username = form.cleaned_data["username"].lower()
        user = User.objects.filter(username__iexact=username).first()

        verified = False
        if user:
            # try security answer
            ans = form.cleaned_data.get("answer")
            if ans and hasattr(user, "security_answer"):
                if user.security_answer.check_answer(ans):
                    verified = True

            # try recovery code
            code = form.cleaned_data.get("recovery_code")
            if code and not verified:
                code_hash = RecoveryCode.hash_code(code.strip().upper())
                rc = RecoveryCode.objects.filter(
                    user=user, code_hash=code_hash, used_at__isnull=True
                ).first()
                if rc:
                    rc.mark_used()   # one-time: burn it now
                    verified = True

        if not verified:
            messages.error(request, "Could not verify. Check your answer or code.")
        else:
            # hand the user a short-lived signed token
            token = signer.sign(user.pk)
            return redirect(f"{reverse('accounts:reset_step2')}?token={token}")

    return render(request, "accounts/reset_step1.html", {"form": form})


# ---------- PASSWORD RESET: STEP 2 (set new password) ----------
@require_http_methods(["GET", "POST"])
def reset_step2(request):
    token = request.GET.get("token") or request.POST.get("token")
    try:
        # valid for 15 minutes (900 seconds)
        user_pk = signer.unsign(token, max_age=900)
        user = User.objects.get(pk=user_pk)
    except (BadSignature, SignatureExpired, User.DoesNotExist, TypeError):
        messages.error(request, "Reset link expired or invalid. Start again.")
        return redirect("accounts:reset_step1")

    form = SetNewPasswordForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user.set_password(form.cleaned_data["password"])
        user.save()
        messages.success(request, "Password updated. Please log in.")
        return redirect("accounts:login")

    return render(request, "accounts/reset_step2.html", {"form": form, "token": token})