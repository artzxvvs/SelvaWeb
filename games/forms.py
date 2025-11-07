from decimal import Decimal

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

from .models import DonationPledge, EmailVerification, Feedback

User = get_user_model()


class SignupForm(UserCreationForm):
    email = forms.EmailField(label="E-mail", max_length=254)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email")

    def clean_email(self):
        email = self.cleaned_data.get("email", "").strip().lower()
        if not email:
            raise forms.ValidationError("Informe um e-mail válido.")
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("Este e-mail já está cadastrado.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"].strip().lower()
        if commit:
            user.save()
        return user


class FeedbackForm(forms.ModelForm):
    impact_rating = forms.IntegerField(
        min_value=1,
        max_value=5,
        label="Impacto percebido",
        help_text="1 = baixo, 5 = alto",
        initial=3,
    )

    class Meta:
        model = Feedback
        fields = ("title", "topic", "impact_rating", "message")
        widgets = {
            "title": forms.TextInput(attrs={"placeholder": "Resumo em uma frase"}),
            "message": forms.Textarea(attrs={"rows": 6, "placeholder": "Compartilhe detalhes que ajudem a equipe a entender o contexto."}),
            "topic": forms.Select(),
        }
        labels = {
            "title": "Título da sugestão",
            "topic": "Área principal",
            "message": "Detalhes",
        }

    def clean_title(self):
        title = self.cleaned_data.get("title", "").strip()
        if len(title) < 8:
            raise forms.ValidationError("Descreva em pelo menos 8 caracteres.")
        return title

    def clean_message(self):
        message = self.cleaned_data.get("message", "").strip()
        if len(message) < 30:
            raise forms.ValidationError("Explique com um pouco mais de detalhes (mínimo de 30 caracteres).")
        return message


class DonationForm(forms.ModelForm):
    amount = forms.DecimalField(
        min_value=Decimal("0.01"),
        max_digits=10,
        decimal_places=2,
        label="Valor da contribuição",
        help_text="Contribua com qualquer valor — cada centavo ajuda a impulsionar a selva criativa.",
    )

    class Meta:
        model = DonationPledge
        fields = ("amount", "is_recurring", "message", "visibility")
        widgets = {
            "message": forms.Textarea(attrs={"rows": 4, "placeholder": "Mensagem opcional para a equipe."}),
            "visibility": forms.Select(),
        }
        labels = {
            "is_recurring": "Quero que seja recorrente",
            "message": "Mensagem para a equipe",
            "visibility": "Privacidade",
        }

    def clean_amount(self):
        amount = self.cleaned_data.get("amount")
        if amount and amount.as_tuple().exponent < -2:
            raise forms.ValidationError("Use no máximo duas casas decimais.")
        return amount


class DonationVerificationForm(forms.Form):
    transaction_code = forms.CharField(
        label="Código da transação Pix",
        max_length=60,
        help_text="Informe o código exibido no comprovante do Pix para validar o pagamento.",
    )

    def clean_transaction_code(self):
        value = self.cleaned_data.get("transaction_code", "").strip().upper()
        if len(value) < 8:
            raise forms.ValidationError("O código deve ter pelo menos 8 caracteres.")
        return value


class EmailAuthenticationForm(AuthenticationForm):
    username = forms.EmailField(label="E-mail", widget=forms.EmailInput(attrs={"autocomplete": "email"}))

    def clean(self):
        email = self.cleaned_data.get("username", "").strip().lower()
        if email:
            try:
                user = User.objects.get(email__iexact=email)
                self.cleaned_data["username"] = user.get_username()
            except User.DoesNotExist:
                # Deixa o fluxo cair no super para garantir mensagem coerente
                self.cleaned_data["username"] = email
        return super().clean()

    def confirm_login_allowed(self, user):
        latest_verification = user.email_verifications.filter(verified_at__isnull=False).first()
        if not latest_verification:
            raise forms.ValidationError(
                "Confirme seu e-mail antes de acessar o portal. Verifique sua caixa de entrada.",
                code="email_not_verified",
            )
        return super().confirm_login_allowed(user)


class EmailVerificationForm(forms.Form):
    email = forms.EmailField(label="E-mail")
    code = forms.CharField(label="Código de verificação", max_length=6)

    def clean(self):
        cleaned = super().clean()
        email = cleaned.get("email", "").strip().lower()
        code = cleaned.get("code", "").strip()
        if not email or not code:
            return cleaned

        try:
            user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            raise forms.ValidationError("Não localizamos uma conta com este e-mail.")

        verification = (
            EmailVerification.objects.filter(user=user, verified_at__isnull=True)
            .order_by("-created_at")
            .first()
        )
        if not verification:
            raise forms.ValidationError("Nenhum código ativo encontrado. Peça um novo envio.")
        if verification.is_expired:
            raise forms.ValidationError("Este código expirou. Solicite um novo envio.")
        if verification.code != code:
            verification.attempts += 1
            verification.save(update_fields=["attempts"])
            raise forms.ValidationError("Código inválido. Confira o e-mail e tente novamente.")

        cleaned["user"] = user
        cleaned["verification"] = verification
        return cleaned


class ResendVerificationForm(forms.Form):
    email = forms.EmailField(label="E-mail")

    def clean_email(self):
        email = self.cleaned_data.get("email", "").strip().lower()
        if not User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("Nenhuma conta encontrada com este e-mail.")
        return email
