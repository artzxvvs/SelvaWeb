from datetime import timedelta
from urllib.parse import parse_qsl, urlsplit, urlunsplit, urlencode as urllib_urlencode

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model, login
from django.contrib.auth.views import LoginView, LogoutView
from django.db.models import Avg, Count, Prefetch, Q, Sum
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.http import urlencode, url_has_allowed_host_and_scheme

from .forms import (
    DonationForm,
    DonationVerificationForm,
    EmailAuthenticationForm,
    EmailVerificationForm,
    FeedbackForm,
    ResendVerificationForm,
    SignupForm,
)
from .models import (
    DonationPaymentStatus,
    DonationPledge,
    EmailVerification,
    FAQCategory,
    FAQEntry,
    Feedback,
    FeedbackStatus,
    Game,
)
from .utils import build_pix_payload, generate_verification_code, qr_code_base64, send_verification_email

User = get_user_model()
KNOWN_EMAIL_COOKIE = "selvacore_known_email"
KNOWN_EMAIL_MAX_AGE = 60 * 60 * 24 * 180  # 180 dias


def home(request):
    games = Game.objects.all()
    has_games = games.exists()
    total_games = games.count()
    today = timezone.localdate()

    featured_game = games.filter(is_featured=True).first()
    if not featured_game:
        featured_game = games.filter(release_date__isnull=False).order_by("release_date").last() or games.first()

    featured_game_id = featured_game.id if featured_game else None

    released_games = (
        games.filter(release_date__isnull=False, release_date__lte=today)
        .exclude(id=featured_game_id)
        .order_by("-release_date")
    )
    upcoming_games = (
        games.filter(release_date__isnull=False, release_date__gt=today)
        .exclude(id=featured_game_id)
        .order_by("release_date")
    )
    unrevealed_games = games.filter(release_date__isnull=True).exclude(id=featured_game_id)

    studio_principles = [
        {
            "title": "Selva viva",
            "description": "Jogabilidade sistêmica, ecossistemas reativos e exploração que recompensa curiosidade.",
        },
        {
            "title": "Tecnologia própria",
            "description": "Ferramentas internas e pipelines automatizados para iterar com segurança e rapidez.",
        },
        {
            "title": "Comunidade no centro",
            "description": "Transparência com jogadores, atualizações frequentes e suporte cross-play desde o primeiro dia.",
        },
    ]

    faq_highlights = (
        FAQEntry.objects.filter(is_active=True, is_featured=True)
        .select_related("category")
        .order_by("category__order", "order")[:6]
    )
    community_updates = Feedback.objects.filter(is_public=True).order_by("-created_at")[:4]
    context_related_categories = FAQCategory.objects.filter(is_active=True).order_by("order")[:4]

    context = {
        "featured_game": featured_game,
        "released_games": released_games,
        "upcoming_games": upcoming_games,
        "unrevealed_games": unrevealed_games,
        "studio_principles": studio_principles,
        "today": today,
        "has_games": has_games,
        "total_games": total_games,
        "faq_highlights": faq_highlights,
        "community_updates": community_updates,
        "context_related_categories": context_related_categories,
    }

    banner_images = []
    for game in games.order_by("-is_featured", "-updated_at"):
        img_url = game.hero_image_url or game.cover_image_url
        if img_url:
            banner_images.append(img_url)
        if len(banner_images) >= 6:
            break

    banner_mode = "default"
    if len(banner_images) >= 2:
        banner_images = [banner_images[1]]
        banner_mode = "second-small"

    context["banner_images"] = banner_images
    context["banner_mode"] = banner_mode

    featured_images = []
    if featured_game:
        if featured_game.hero_image_url:
            featured_images.append(featured_game.hero_image_url)
        if featured_game.cover_image_url and featured_game.cover_image_url not in featured_images:
            featured_images.append(featured_game.cover_image_url)

    context["featured_images"] = featured_images

    return render(request, "games/home.html", context)


def _safe_next_url(request, candidate, fallback):
    if candidate and url_has_allowed_host_and_scheme(candidate, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
        return candidate
    return fallback


def community_portal(request, focus=None):
    categories = (
        FAQCategory.objects.filter(is_active=True)
        .prefetch_related(
            Prefetch("faqs", queryset=FAQEntry.objects.filter(is_active=True).order_by("order", "question"))
        )
        .order_by("order", "title")
    )

    active_focus = focus or request.GET.get("focus") or "faq"

    feedback_queryset = Feedback.objects.all()
    public_feedback = (
        feedback_queryset.filter(is_public=True)
        .select_related("user")
        .order_by("-created_at")[:6]
    )

    feedback_metrics = feedback_queryset.aggregate(
        total=Count("id"),
        pending=Count("id", filter=Q(status=FeedbackStatus.NEW)),
        reviewing=Count("id", filter=Q(status=FeedbackStatus.IN_REVIEW)),
        published=Count("id", filter=Q(status=FeedbackStatus.PUBLISHED)),
        avg_impact=Avg("impact_rating"),
    )

    donation_queryset = DonationPledge.objects.all()
    donation_metrics = donation_queryset.aggregate(
        supporters=Count("user", distinct=True),
        total=Sum("amount"),
        recurring=Count("id", filter=Q(is_recurring=True)),
    )

    feedback_form = FeedbackForm()
    donation_form = DonationForm()
    verification_form = DonationVerificationForm()

    if request.method == "POST":
        action = request.POST.get("action")
        if action == "feedback":
            active_focus = "feedback"
            if not request.user.is_authenticated:
                login_target = f"{reverse('faq')}?focus=feedback"
                messages.error(request, "É necessário entrar com sua conta para enviar contribuições.")
                query_string = urlencode({"next": login_target})
                return redirect(f"{reverse('login')}?{query_string}")
            feedback_form = FeedbackForm(request.POST)
            if feedback_form.is_valid():
                feedback = feedback_form.save(commit=False)
                feedback.user = request.user
                feedback.save()
                messages.success(request, "Obrigado! Sua sugestão foi recebida e entra na fila de análise.")
                return HttpResponseRedirect(f"{reverse('faq')}?focus=feedback#feedback")
        elif action == "donation":
            active_focus = "donation"
            if not request.user.is_authenticated:
                login_target = reverse('donate')
                messages.error(request, "Crie uma conta ou entre para registrar sua intenção de apoio.")
                query_string = urlencode({"next": login_target})
                return redirect(f"{reverse('login')}?{query_string}")
            donation_form = DonationForm(request.POST)
            if donation_form.is_valid():
                pledge = donation_form.save(commit=False)
                pledge.user = request.user
                pledge.save()
                messages.success(request, "Recebemos sua contribuição! Vamos entrar em contato com instruções de pagamento.")
                return HttpResponseRedirect(f"{reverse('donate')}?focus=donation#donation")
        elif action == "verify_pix":
            active_focus = "donation"
            if not request.user.is_authenticated:
                messages.error(request, "É necessário estar autenticado para validar o Pix.")
                return redirect(f"{reverse('login')}?{urlencode({'next': reverse('donate')})}")
            verification_form = DonationVerificationForm(request.POST)
            if verification_form.is_valid():
                pledge = get_object_or_404(DonationPledge, id=request.POST.get("pledge_id"), user=request.user)
                code = verification_form.cleaned_data["transaction_code"]
                pledge.pix_transaction_code = code
                pledge.pix_last_checked_at = timezone.now()
                expected_txid = getattr(settings, "PIX_STATIC_TXID", "").strip() or pledge.pix_txid
                matches_txid = expected_txid and expected_txid.lower() in code.lower()
                if matches_txid:
                    pledge.pix_status = DonationPaymentStatus.CONFIRMED
                    pledge.pix_confirmed_at = timezone.now()
                    pledge.save(update_fields=[
                        "pix_transaction_code",
                        "pix_status",
                        "pix_confirmed_at",
                        "pix_last_checked_at",
                    ])
                    messages.success(request, "Pix confirmado! Obrigado por alimentar a selva criativa.")
                else:
                    pledge.pix_status = DonationPaymentStatus.FAILED
                    pledge.save(update_fields=[
                        "pix_transaction_code",
                        "pix_status",
                        "pix_last_checked_at",
                    ])
                    messages.warning(request, "Não conseguimos localizar o pagamento com este código. Revise o TXID no comprovante.")
                return HttpResponseRedirect(f"{reverse('donate')}?focus=donation#donation")

    user_donations = []
    if request.user.is_authenticated:
        pix_key = getattr(settings, "PIX_KEY", "")
        merchant_name = getattr(settings, "PIX_MERCHANT_NAME", "SelvaCore Studios")
        merchant_city = getattr(settings, "PIX_MERCHANT_CITY", "SAO PAULO")
        description = getattr(settings, "PIX_DESCRIPTION", "SelvaCore Community")
        static_payload = getattr(settings, "PIX_STATIC_PAYLOAD", "").strip()
        static_txid = getattr(settings, "PIX_STATIC_TXID", "").strip()
        for pledge in request.user.donation_pledges.order_by("-created_at")[:5]:
            try:
                if static_payload:
                    payload = static_payload
                elif pix_key:
                    payload = build_pix_payload(
                        key=pix_key,
                        txid=pledge.pix_txid,
                        amount=pledge.amount,
                        merchant_name=merchant_name,
                        merchant_city=merchant_city,
                        description=description,
                    )
                else:
                    payload = ""
            except Exception:
                payload = ""
            qr_image = qr_code_base64(payload) if payload else ""
            user_donations.append(
                {
                    "pledge": pledge,
                    "payload": payload,
                    "qr_image": qr_image,
                    "txid_display": static_txid or pledge.pix_txid,
                }
            )

    context = {
        "categories": categories,
        "public_feedback": public_feedback,
        "feedback_metrics": feedback_metrics,
        "donation_metrics": donation_metrics,
        "feedback_form": feedback_form,
        "donation_form": donation_form,
        "verification_form": verification_form,
        "active_focus": active_focus,
        "user_donations": user_donations,
        "donation_status": DonationPaymentStatus,
    }
    return render(request, "games/community_portal.html", context)


def donate(request):
    return community_portal(request, focus="donation")


def _remember_known_email(response, email: str):
    if not email:
        return response
    response.set_cookie(
        KNOWN_EMAIL_COOKIE,
        email,
        max_age=KNOWN_EMAIL_MAX_AGE,
        samesite="Lax",
        httponly=True,
    )
    return response


def _append_query(url: str, extra_params: dict[str, str]) -> str:
    if not extra_params:
        return url
    split = urlsplit(url)
    query = dict(parse_qsl(split.query))
    query.update({key: value for key, value in extra_params.items() if value is not None})
    new_query = urllib_urlencode(query)
    return urlunsplit((split.scheme, split.netloc, split.path, new_query, split.fragment))


class SelvaLoginView(LoginView):
    template_name = "account/login.html"
    authentication_form = EmailAuthenticationForm
    redirect_authenticated_user = True

    def get_initial(self):
        initial = super().get_initial()
        email_hint = self.request.GET.get("email")
        if email_hint:
            initial["username"] = email_hint
        return initial

    def form_valid(self, form):
        response = super().form_valid(form)
        user = self.request.user
        if user and user.is_authenticated:
            _remember_known_email(response, user.email)
        return response


class SelvaLogoutView(LogoutView):
    def get_next_page(self):
        target = super().get_next_page()
        if not target:
            return target
        return _append_query(target, {"novo": "1"})

    def dispatch(self, request, *args, **kwargs):
        remembered_email = ""
        if request.user.is_authenticated:
            remembered_email = request.user.email
        else:
            remembered_email = request.COOKIES.get(KNOWN_EMAIL_COOKIE, "")
        response = super().dispatch(request, *args, **kwargs)
        if response and remembered_email:
            _remember_known_email(response, remembered_email)
        return response


def signup(request):
    if request.user.is_authenticated:
        return redirect("faq")

    known_email = request.COOKIES.get(KNOWN_EMAIL_COOKIE, "").strip().lower()
    default_redirect = reverse("faq")
    next_url = _safe_next_url(request, request.GET.get("next"), default_redirect)
    force_signup = request.GET.get("novo") == "1" or request.POST.get("force_signup") == "1"

    if known_email and not force_signup:
        messages.info(
            request,
            "Identificamos uma conta recente neste dispositivo. Use seu login para entrar rapidamente ou solicite um novo cadastro explicitamente.",
        )
        login_params = {"next": next_url} if next_url else {}
        login_params["retorno"] = "signup"
        response = redirect(f"{reverse('login')}?{urlencode(login_params)}")
        return _remember_known_email(response, known_email)

    if request.method == "POST":
        posted_email = request.POST.get("email", "").strip().lower()
        if posted_email:
            existing_user = User.objects.filter(email__iexact=posted_email).first()
            if existing_user:
                verified = existing_user.email_verifications.filter(verified_at__isnull=False).exists()
                if verified:
                    messages.info(request, "Este e-mail já possui cadastro. Entre com sua senha para continuar.")
                    login_params = {"next": next_url} if next_url else {}
                    login_params["email"] = posted_email
                    response = redirect(f"{reverse('login')}?{urlencode(login_params)}")
                    return _remember_known_email(response, existing_user.email)
                code = generate_verification_code()
                expires_at = timezone.now() + timedelta(minutes=30)
                EmailVerification.objects.create(user=existing_user, code=code, expires_at=expires_at)
                send_verification_email(existing_user, code)
                messages.success(request, "Reenviamos o código de verificação. Valide o e-mail para destravar o portal.")
                params = {"email": existing_user.email}
                if next_url:
                    params["next"] = next_url
                response = redirect(f"{reverse('verify_email')}?{urlencode(params)}")
                return _remember_known_email(response, existing_user.email)
        form = SignupForm(request.POST)
        if form.is_valid():
            user = form.save()
            code = generate_verification_code()
            expires_at = timezone.now() + timedelta(minutes=30)
            EmailVerification.objects.create(user=user, code=code, expires_at=expires_at)
            send_verification_email(user, code)
            messages.success(request, "Cadastro concluído! Enviamos um código para confirmar seu e-mail.")
            params = {"email": user.email}
            post_next = _safe_next_url(request, request.POST.get("next"), default_redirect)
            if post_next:
                params["next"] = post_next
            response = redirect(f"{reverse('verify_email')}?{urlencode(params)}")
            return _remember_known_email(response, user.email)
    else:
        form = SignupForm()

    context = {
        "form": form,
        "next": next_url,
        "force_signup": force_signup,
    }
    return render(request, "account/signup.html", context)


def verify_email(request):
    default_redirect = reverse("faq")
    next_param = request.GET.get("next") or request.POST.get("next")
    next_url = _safe_next_url(request, next_param, default_redirect)
    email_initial = request.GET.get("email") or request.POST.get("email") or ""

    verification_form = EmailVerificationForm(initial={"email": email_initial})
    resend_form = ResendVerificationForm(initial={"email": email_initial})

    if request.method == "POST":
        action = request.POST.get("action")
        if action == "verify":
            verification_form = EmailVerificationForm(request.POST)
            resend_form = ResendVerificationForm(initial={"email": request.POST.get("email", "")})
            if verification_form.is_valid():
                user = verification_form.cleaned_data["user"]
                verification = verification_form.cleaned_data["verification"]
                verification.mark_verified()
                login(request, user)
                messages.success(request, "E-mail confirmado! Bem-vindo à comunidade SelvaCore.")
                redirect_target = _safe_next_url(request, request.POST.get("next"), default_redirect)
                response = redirect(redirect_target)
                return _remember_known_email(response, user.email)
        elif action == "resend":
            resend_form = ResendVerificationForm(request.POST)
            verification_form = EmailVerificationForm(initial={"email": request.POST.get("email", "")})
            if resend_form.is_valid():
                email = resend_form.cleaned_data["email"]
                user = User.objects.get(email__iexact=email)
                code = generate_verification_code()
                expires_at = timezone.now() + timedelta(minutes=30)
                EmailVerification.objects.create(user=user, code=code, expires_at=expires_at)
                send_verification_email(user, code)
                messages.success(request, "Enviamos um novo código de verificação!")
                params = {"email": user.email}
                if next_url:
                    params["next"] = next_url
                return redirect(f"{reverse('verify_email')}?{urlencode(params)}")

    context = {
        "verification_form": verification_form,
        "resend_form": resend_form,
        "next": next_url,
    }
    return render(request, "account/verify_email.html", context)

