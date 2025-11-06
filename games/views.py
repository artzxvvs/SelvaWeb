from django.shortcuts import render
from django.utils import timezone

from .models import Game


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

    context = {
        "featured_game": featured_game,
        "released_games": released_games,
        "upcoming_games": upcoming_games,
        "unrevealed_games": unrevealed_games,
        "studio_principles": studio_principles,
        "today": today,
        "has_games": has_games,
        "total_games": total_games,
    }

    # Banner carousel images: priorize jogos destacados, depois os demais com imagens
    banner_images = []
    for g in games.order_by('-is_featured', '-updated_at'):
        img_url = g.hero_image_url or g.cover_image_url
        if img_url:
            banner_images.append(img_url)
        if len(banner_images) >= 6:
            break

    # If there are at least 2 images, user requested to show only the second one as a reduced banner
    banner_mode = "default"
    if len(banner_images) >= 2:
        banner_images = [banner_images[1]]
        banner_mode = "second-small"

    context["banner_images"] = banner_images
    context["banner_mode"] = banner_mode

    # Featured card images (small carousel inside the featured card)
    featured_images = []
    if featured_game:
        # Prioriza hero, depois capa
        if featured_game.hero_image_url:
            featured_images.append(featured_game.hero_image_url)
        if featured_game.cover_image_url and featured_game.cover_image_url not in featured_images:
            featured_images.append(featured_game.cover_image_url)

    context["featured_images"] = featured_images

    return render(request, "games/home.html", context)