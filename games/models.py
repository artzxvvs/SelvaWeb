import uuid

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone


class GameStatus(models.TextChoices):
    PRE_PRODUCTION = "pre_production", "Pré-produção"
    IN_DEVELOPMENT = "in_development", "Em desenvolvimento"
    EARLY_ACCESS = "early_access", "Acesso antecipado"
    RELEASED = "released", "Lançado"
    ARCHIVED = "archived", "Arquivado"


class Game(models.Model):
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True)
    tagline = models.CharField(max_length=200, blank=True)
    short_description = models.CharField(max_length=400, blank=True)
    long_description = models.TextField(blank=True)
    genre = models.CharField(max_length=120, blank=True)
    platforms = models.CharField(max_length=180, blank=True, help_text="Lista separada por vírgula (ex.: PC, Xbox, PlayStation)")
    status = models.CharField(max_length=32, choices=GameStatus.choices, default=GameStatus.IN_DEVELOPMENT)
    cover_image = models.URLField(blank=True, help_text="URL alternativa para a arte de capa, caso não envie arquivo")
    cover_image_upload = models.ImageField(upload_to="games/covers/", blank=True)
    hero_image_upload = models.ImageField(upload_to="games/hero/", blank=True)
    release_date = models.DateField(null=True, blank=True)
    trailer_url = models.URLField(blank=True)
    is_featured = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-is_featured", "-release_date", "title"]
        verbose_name = "jogo"
        verbose_name_plural = "jogos"

    def __str__(self):
        return self.title

    @property
    def cover_image_url(self):
        if self.cover_image_upload:
            return self.cover_image_upload.url
        return self.cover_image

    @property
    def hero_image_url(self):
        if self.hero_image_upload:
            return self.hero_image_upload.url
        return self.cover_image_url

    @property
    def has_release_date(self):
        return bool(self.release_date)


class FAQCategory(models.Model):
    slug = models.SlugField(max_length=60, unique=True)
    title = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["order", "title"]
        verbose_name = "categoria de FAQ"
        verbose_name_plural = "categorias de FAQ"

    def __str__(self):
        return self.title


class FAQEntry(models.Model):
    class Audience(models.TextChoices):
        COMMUNITY = "community", "Comunidade"
        PARTNERS = "partners", "Parceiros"
        TEAM = "team", "Equipe interna"
        GENERAL = "general", "Geral"

    category = models.ForeignKey(FAQCategory, on_delete=models.CASCADE, related_name="faqs")
    question = models.CharField(max_length=220)
    answer = models.TextField()
    audience = models.CharField(max_length=32, choices=Audience.choices, default=Audience.GENERAL)
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)

    class Meta:
        ordering = ["category", "order", "question"]
        verbose_name = "pergunta frequente"
        verbose_name_plural = "perguntas frequentes"

    def __str__(self):
        return self.question


class FeedbackTopic(models.TextChoices):
    GAMEPLAY = "gameplay", "Jogabilidade"
    ART_AND_UI = "art_ui", "Arte e interface"
    TECHNOLOGY = "technology", "Tecnologia e performance"
    COMMUNITY = "community", "Comunidade"
    BUSINESS = "business", "Parcerias e negócio"
    OTHER = "other", "Outro"


class FeedbackStatus(models.TextChoices):
    NEW = "new", "Recebido"
    IN_REVIEW = "in_review", "Em análise"
    ACKNOWLEDGED = "acknowledged", "Planejado"
    PUBLISHED = "published", "Publicado"


class Feedback(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="feedback_items")
    title = models.CharField(max_length=140)
    topic = models.CharField(max_length=32, choices=FeedbackTopic.choices, default=FeedbackTopic.OTHER)
    message = models.TextField()
    impact_rating = models.PositiveSmallIntegerField(
        default=3,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Escala de 1 (baixo) a 5 (alto)",
    )
    status = models.CharField(max_length=24, choices=FeedbackStatus.choices, default=FeedbackStatus.NEW)
    is_public = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "feedback da comunidade"
        verbose_name_plural = "feedbacks da comunidade"

    def __str__(self):
        return f"{self.title} ({self.get_topic_display()})"

    @property
    def short_message(self):
        return (self.message[:120] + "...") if len(self.message) > 123 else self.message


class EmailVerification(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="email_verifications")
    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    verified_at = models.DateTimeField(null=True, blank=True)
    attempts = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "verificação de e-mail"
        verbose_name_plural = "verificações de e-mail"

    def __str__(self):
        status = "verificado" if self.verified_at else "pendente"
        return f"{self.user} - {self.code} ({status})"

    @property
    def is_expired(self):
        return timezone.now() >= self.expires_at

    @property
    def is_verified(self):
        return bool(self.verified_at)

    def mark_verified(self):
        self.verified_at = timezone.now()
        self.save(update_fields=["verified_at"])


class DonationVisibility(models.TextChoices):
    PRIVATE = "private", "Privado"
    TEAM_ONLY = "team_only", "Visível para a equipe"
    PUBLIC = "public", "Pode ser exibido"


class DonationPaymentStatus(models.TextChoices):
    PENDING = "pending", "Aguardando Pix"
    AWAITING_CONFIRMATION = "awaiting_confirmation", "Comprovante enviado"
    CONFIRMED = "confirmed", "Pix confirmado"
    FAILED = "failed", "Pagamento não localizado"


class DonationPledge(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="donation_pledges")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default="BRL")
    message = models.TextField(blank=True)
    is_recurring = models.BooleanField(default=False)
    visibility = models.CharField(max_length=16, choices=DonationVisibility.choices, default=DonationVisibility.TEAM_ONLY)
    created_at = models.DateTimeField(auto_now_add=True)
    pix_txid = models.CharField(max_length=25, unique=True, blank=True)
    pix_status = models.CharField(max_length=24, choices=DonationPaymentStatus.choices, default=DonationPaymentStatus.PENDING)
    pix_transaction_code = models.CharField(max_length=60, blank=True)
    pix_confirmed_at = models.DateTimeField(null=True, blank=True)
    pix_last_checked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "promessa de doação"
        verbose_name_plural = "promessas de doação"

    def __str__(self):
        return f"{self.user} - {self.amount} {self.currency}"

    def save(self, *args, **kwargs):
        if not self.pix_txid:
            self.pix_txid = uuid.uuid4().hex[:25].upper()
        super().save(*args, **kwargs)

    @property
    def is_confirmed(self):
        return self.pix_status == DonationPaymentStatus.CONFIRMED and self.pix_confirmed_at is not None