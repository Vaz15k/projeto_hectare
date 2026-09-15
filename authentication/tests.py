from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.http import HttpResponse
from django.test import RequestFactory, SimpleTestCase, TestCase
from django.urls import reverse
from django_ratelimit.exceptions import Ratelimited

from authentication.views import client_ip, login_account, login_ratelimit


class LoginHelpersTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()
        cache.clear()
        self.addCleanup(cache.clear)

    def test_ip_proxy_e_fallback(self):
        for proxy, esperado in [('203.0.113.1', '203.0.113.1'), ('', '127.0.0.1')]:
            with self.subTest(proxy=proxy):
                self.assertEqual(client_ip(self.factory.get('/', HTTP_X_REAL_IP=proxy)), esperado)

    def test_normaliza_login_principal_e_admin(self):
        for dados in ({'login': '  USUARIO  '}, {'username': '  USUARIO  '}, {}):
            with self.subTest(dados=dados):
                self.assertEqual(login_account('', self.factory.post('/', dados)), 'usuario' if dados else '')

    @patch('django_ratelimit.core.time.time', return_value=1800000000)
    def test_sexta_tentativa_bloqueada_por_ip_ou_conta(self, _clock):
        view = login_ratelimit(lambda request: HttpResponse('ok'))
        for modo in ('ip', 'conta'):
            cache.clear()
            with self.subTest(modo=modo):
                for i in range(6):
                    request = self.factory.post('/', {'login': f'conta{i}' if modo == 'ip' else 'mesma'},
                                                REMOTE_ADDR='192.0.2.1' if modo == 'ip' else f'192.0.2.{i + 1}')
                    if i < 5:
                        self.assertEqual(view(request).status_code, 200)
                    else:
                        with self.assertRaises(Ratelimited):
                            view(request)

    def test_get_nao_consume_limite(self):
        view = login_ratelimit(lambda request: HttpResponse('ok'))
        for _ in range(10):
            self.assertEqual(view(self.factory.get('/')).status_code, 200)


class LoginIntegrationTests(TestCase):
    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)
        get_user_model().objects.create_user(username='operador', password='senha-teste')

    def test_login_nao_redireciona_para_site_externo(self):
        response = self.client.post(reverse('login') + '?next=https://example.org',
                                    {'login': 'operador', 'password': 'senha-teste'})
        self.assertRedirects(response, reverse('home'), fetch_redirect_response=False)
        self.assertIn('_auth_user_id', self.client.session)

    def test_logout_exige_post(self):
        self.client.login(username='operador', password='senha-teste')
        self.assertEqual(self.client.get(reverse('logout')).status_code, 405)
        self.assertIn('_auth_user_id', self.client.session)
        self.assertEqual(self.client.post(reverse('logout')).status_code, 302)
        self.assertNotIn('_auth_user_id', self.client.session)

    @patch('django_ratelimit.core.time.time', return_value=1800000000)
    def test_login_exibe_429_apos_limite(self, _clock):
        for _ in range(5):
            self.assertEqual(self.client.post(reverse('login'), {'login': 'invalido'}).status_code, 200)
        response = self.client.post(reverse('login'), {'login': 'invalido'})
        self.assertEqual(response.status_code, 429)
        self.assertTrue(response.context['ratelimited'])
