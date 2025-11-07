from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils.http import urlencode

from .models import DonationPledge, FAQCategory, FAQEntry, Feedback


class CommunityPortalTests(TestCase):
    def setUp(self):
        self.category = FAQCategory.objects.create(slug="geral", title="Geral", description="Visão macro")
        FAQEntry.objects.create(
            category=self.category,
            question="Como funciona o feedback?",
            answer="Nós triamos todas as entradas semanalmente.",
            audience=FAQEntry.Audience.COMMUNITY,
            order=1,
        )
        self.user = get_user_model().objects.create_user(
            username="tester",
            email="tester@example.com",
            password="segredo123",
        )

    def test_portal_renders_with_category(self):
        response = self.client.get(reverse("faq"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Portal da Comunidade")
        self.assertContains(response, self.category.title)

    def test_feedback_requires_authentication(self):
        response = self.client.post(
            reverse("faq"),
            {
                "action": "feedback",
                "title": "Sugestão legal",
                "topic": "other",
                "impact_rating": 3,
                "message": "Este é um feedback de teste com detalhes suficientes para passar na validação.",
            },
        )
        target = f"{reverse('faq')}?focus=feedback"
        login_url = f"{reverse('login')}?{urlencode({'next': target})}"
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, login_url)
        self.assertEqual(Feedback.objects.count(), 0)

    def test_authenticated_user_can_submit_feedback(self):
        self.client.login(username="tester", password="segredo123")
        response = self.client.post(
            reverse("faq"),
            {
                "action": "feedback",
                "title": "Sugestão relevante",
                "topic": "gameplay",
                "impact_rating": 4,
                "message": "Feedback detalhado para validar o fluxo completo e garantir que o registro aconteça.",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn("#feedback", response.url)
        self.assertEqual(Feedback.objects.count(), 1)
        feedback = Feedback.objects.first()
        self.assertEqual(feedback.user, self.user)
        self.assertEqual(feedback.topic, "gameplay")

    def test_authenticated_user_can_register_donation(self):
        self.client.login(username="tester", password="segredo123")
        response = self.client.post(
            reverse("donate"),
            {
                "action": "donation",
                "amount": "35",
                "is_recurring": "on",
                "message": "Quero apoiar mensalmente a SelvaCore.",
                "visibility": "team_only",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn("#donation", response.url)
        self.assertEqual(DonationPledge.objects.count(), 1)
        pledge = DonationPledge.objects.first()
        self.assertEqual(pledge.user, self.user)
        self.assertTrue(pledge.is_recurring)
