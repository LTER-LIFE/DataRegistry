from flask import session, url_for
import flask_babel as babel

from test.base_test_case import BaseTestCase


class TestI18n(BaseTestCase):
    def test_default_language_is_english(self):
        with self.app.test_request_context():
            assert babel.gettext('About') == 'About'

    def test_language_can_be_changed_to_dutch(self):
        with self.client:
            with self.app.app_context():
                self.client.get(
                    url_for('main_bp.set_language', language_key='nl')
                )

            assert session['language'] == 'nl'
            assert babel.gettext('About') == 'Over'

    def test_requesting_an_unsupported_language_defaults_to_english(self):
        with self.client:
            with self.app.app_context():
                self.client.get(
                    url_for('main_bp.set_language', language_key='de')
                )

            assert session['language'] == 'en'
            assert babel.gettext('About') == 'About'
