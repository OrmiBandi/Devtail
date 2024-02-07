import uuid
from typing import Any
from django.http.response import HttpResponse
from django.urls import reverse
from django.contrib import messages
from django.urls import reverse_lazy
from django.shortcuts import redirect, render
from django.core.mail import EmailMessage
from django.contrib.auth import get_user_model
from django.contrib.auth.views import (
    LoginView,
    PasswordResetView,
    PasswordResetConfirmView,
)
from django.db.models.base import Model as Model
from django.views.generic.edit import UpdateView, DeleteView
from django.utils.translation import gettext_lazy as _
from django.views.generic import CreateView, DetailView
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.sites.shortcuts import get_current_site
from django.http import HttpRequest, HttpResponseBadRequest
from django.utils.http import urlsafe_base64_decode
from allauth.account.views import LogoutView
from allauth.socialaccount.views import SignupView as BaseSignupView

from .forms import (
    SignupForm,
    CustomLoginForm,
    AccountUpdateForm,
    AccountDeleteForm,
    PasswordChangeForm,
)

User = get_user_model()


class SignupView(CreateView):
    """
    회원가입 View
    """

    model = User
    form_class = SignupForm
    template_name = "accounts/signup.html"
    success_url = reverse_lazy("accounts:login")

    def post(self, request, *args, **kwargs):
        """
        회원가입 메서드
        """
        form = self.form_class(request.POST)
        if form.is_valid():
            token = uuid.uuid4()
            user = form.save(commit=False)
            if "profile_image" in request.FILES:
                profile_image = request.FILES["profile_image"]
                user.profile_image = profile_image
            user.auth_code = token
            user.save()
            domain = get_current_site(request).domain
            confirm_link = (
                f'http://{domain}{reverse("accounts:email_confirm", args=[token])}'
            )

            title = "deVtail 인증 메일입니다."
            message = (
                "인증을 완료하시려면 링크를 클릭해주세요.\n인증 URL: " + confirm_link
            )
            email = EmailMessage(title, message, "elwl5515@gmail.com", [user.email])
            email.send()
            messages.success(request, "인증 URL이 전송되었습니다. 메일을 확인해주세요.")
            return redirect("accounts:login")
        else:
            context = {}
            for msg in form.errors.as_data():
                context[f"error_{msg}"] = form.errors[msg][0]
            return render(
                request,
                self.template_name,
                context,
                status=HttpResponseBadRequest.status_code,
            )


class SocialSignupView(BaseSignupView):
    template_name = "accounts/signup.html"


def email_confirm(request, token):
    """
    이메일 인증 메서드
    """
    User = get_user_model()
    user = User.objects.get(auth_code=token)
    user.auth_code = None
    user.is_active = True
    user.save()
    messages.success(
        request, "이메일 인증이 완료되었습니다. 회원가입이 완료되었습니다."
    )
    return redirect("accounts:login")


class CustomLoginView(LoginView):
    """
    로그인 View
    """

    template_name = "accounts/login.html"
    form_class = CustomLoginForm
    redirect_authenticated_user = True

    def post(self, request: HttpRequest, *args: str, **kwargs: Any) -> HttpResponse:
        """
        로그인 메서드
        """
        form = self.get_form()
        if form.is_valid():
            return self.form_valid(form)
        else:
            return self.form_invalid(form)

    def get_success_url(self) -> Any:
        """
        로그인 성공시 이동할 URL
        """
        url = self.get_redirect_url()
        return url or reverse_lazy("main:home")

    def form_invalid(self, form: AuthenticationForm):
        """
        로그인 실패시 메서드
        """
        form_errors = form.errors.get("__all__", [])
        if "존재하지 않는 사용자이거나 비밀번호가 일치하지 않습니다." in form_errors:
            return HttpResponseBadRequest(
                _("존재하지 않는 사용자이거나 비밀번호가 일치하지 않습니다.")
            )
        elif "이메일을 입력해주세요." in form_errors:
            return HttpResponseBadRequest(_("이메일을 입력해주세요."))
        elif "비밀번호를 입력해주세요." in form_errors:
            return HttpResponseBadRequest(_("비밀번호를 입력해주세요."))


class CustomLogoutView(LogoutView):
    """
    로그아웃 View
    """

    def dispatch(self, request, *args, **kwargs):
        """
        로그아웃 메서드
        """
        if not request.user.is_authenticated:
            return HttpResponseBadRequest(_("로그인되지 않은 사용자입니다."))
        return super().dispatch(request, *args, **kwargs)


class ProfileView(LoginRequiredMixin, DetailView):
    login_url = "/accounts/login/"
    model = User
    template_name = "accounts/profile.html"
    context_object_name = "user_profile"

    def handle_no_permission(self):
        """
        로그인 하지 않은 사용자의 경우
        "로그인되지 않은 사용자입니다."라는
        메시지를 에러 메시지에 담는 메서드
        """
        return HttpResponse(_("로그인되지 않은 사용자입니다."), status=401)

    def get_object(self):
        """
        입력받은 pk 값의 유저를 반환하는 메서드
        """
        pk = self.kwargs.get("pk")
        obj = User.objects.filter(pk=pk).first()
        return obj

    def get(self, request, *args, **kwargs):
        """
        프로필 요청을 처리하는 get 메서드
            - pk로 조회한 유저의 프로필이 없는 경우 404 에러 반환
        """
        obj = self.get_object()
        if not obj:
            return HttpResponse(_("존재하지 않는 사용자입니다."), status=404)
        return super().get(request, *args, **kwargs)


class AccountUpdateView(LoginRequiredMixin, UpdateView):
    model = User
    template_name = "accounts/account_update.html"
    form_class = AccountUpdateForm
    context_object_name = "account"

    def get_success_url(self):
        """
        수정 성공 시 프로필 페이지로 이동시키는 메서드
        """
        return reverse_lazy("profile", kwargs={"pk": self.object.pk})

    def handle_no_permission(self):
        """
        로그인 하지 않은 사용자의 경우
        "로그인되지 않은 사용자입니다."라는
        메시지를 에러 메시지에 담는 메서드
        """
        return HttpResponse(_("로그인되지 않은 사용자입니다."), status=401)

    def get_object(self, queryset=None):
        """
        현재 로그인한 유저를 반환하는 메서드
        """
        return self.request.user

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, "사용자 정보가 수정되었습니다.")
        return response

    def form_invalid(self, form):
        response = super().form_invalid(form)
        messages.error(self.request, "사용자 정보 수정에 실패했습니다.")
        return response

    def post(self, request: HttpRequest, *args: str, **kwargs: Any) -> HttpResponse:
        response = super().post(request, *args, **kwargs)
        form = self.get_form()
        if not form.is_valid():
            error_message = str(list(form.errors.as_data().values())[0][0].messages[0])
            return HttpResponseBadRequest(error_message)
        return response


class AccountDeleteView(LoginRequiredMixin, DeleteView):
    model = User
    form_class = AccountDeleteForm
    template_name = "accounts/account_delete.html"
    context_object_name = "account"
    success_url = reverse_lazy("home")

    def form_valid(self, form):
        password = form.cleaned_data["password"]
        user = self.request.user
        if user.check_password(password):
            messages.success(self.request, "회원 탈퇴가 완료되었습니다.")
            return super(AccountDeleteView, self).delete(
                self.request, *self.args, **self.kwargs
            )
        else:
            error_message = "비밀번호가 일치하지 않습니다."
            return HttpResponseBadRequest(error_message)

    def get_object(self, queryset=None):
        return self.request.user

    def handle_no_permission(self):
        """
        로그인 하지 않은 사용자의 경우
        "로그인되지 않은 사용자입니다."라는
        메시지를 에러 메시지에 담는 메서드
        """
        return HttpResponse(_("로그인되지 않은 사용자입니다."), status=401)

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        form = self.get_form()
        if not form.is_valid():
            error_message = str(list(form.errors.as_data().values())[0][0].messages[0])
            return HttpResponseBadRequest(error_message)
        return response


class PasswordChangeView(LoginRequiredMixin, UpdateView):
    model = User
    template_name = "accounts/password_change.html"
    form_class = PasswordChangeForm
    context_object_name = "account"

    def get_success_url(self):
        """
        수정 성공 시 프로필 페이지로 이동시키는 메서드
        """
        return reverse_lazy("profile", kwargs={"pk": self.object.pk})

    def handle_no_permission(self):
        """
        로그인 하지 않은 사용자의 경우
        "로그인되지 않은 사용자입니다."라는
        메시지를 에러 메시지에 담는 메서드
        """
        return HttpResponse(_("로그인되지 않은 사용자입니다."), status=401)

    def get_object(self, queryset=None):
        """
        현재 로그인한 유저를 반환하는 메서드
        """
        return self.request.user

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, "비밀번호가 변경되었습니다.")
        return response

    def form_invalid(self, form):
        response = super().form_invalid(form)
        messages.error(self.request, "비밀번호 변경에 실패했습니다.")
        return response

    def post(self, request: HttpRequest, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        form = self.get_form()
        if not form.is_valid():
            error_message = str(list(form.errors.as_data().values())[0][0].messages[0])
            return HttpResponseBadRequest(error_message)
        return response

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs


class PasswordResetCustomView(PasswordResetView):
    template_name = "accounts/password_find.html"
    email_template_name = "registration/password_reset_email.html"
    subject_template_name = "accounts/password_reset_subject.txt"
    success_url = reverse_lazy("login")

    def form_valid(self, form):
        email = form.cleaned_data["email"]
        if not User.objects.filter(email=email).exists():
            return HttpResponseBadRequest("존재하지 않는 이메일입니다.")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        print(get_current_site(self.request).domain)
        context.update({"domain": get_current_site(self.request).domain})
        return context


class PasswordResetConfirmCustomView(PasswordResetConfirmView):
    template_name = "accounts/password_reset.html"
    success_url = reverse_lazy("login")

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)

    def dispatch(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        uidb64 = kwargs["uidb64"]
        token = kwargs["token"]

        uid = urlsafe_base64_decode(uidb64).decode()
        user = User.objects.get(pk=uid)
        if not self.token_generator.check_token(user, token):
            raise ValueError("The password reset link is invalid")

        return super().dispatch(request, *args, **kwargs)

    def post(self, request: HttpRequest, *args: str, **kwargs: Any) -> HttpResponse:
        return super().post(request, *args, **kwargs)

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, "비밀번호가 초기화되었습니다.")
        return response


signup = SignupView.as_view()
social_signup = SocialSignupView.as_view()
login = CustomLoginView.as_view()
logout = CustomLogoutView.as_view()
profile = ProfileView.as_view()
account_update = AccountUpdateView.as_view()
account_delete = AccountDeleteView.as_view()
password_change = PasswordChangeView.as_view()
password_reset = PasswordResetCustomView.as_view()
password_reset_confirm = PasswordResetConfirmCustomView.as_view()
