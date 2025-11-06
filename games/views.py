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

    return render(request, "games/home.html", context)