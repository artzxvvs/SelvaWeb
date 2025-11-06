from django.db import models


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