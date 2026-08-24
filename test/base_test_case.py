import unittest

from application import create_app


class BaseTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # setup test client
        cls.app = create_app()
        cls.app.config.update({
            "SERVER_NAME": "localhost.dev",
            "TESTING": True,
            "WTF_CSRF_ENABLED": False,
        })

        cls.client = cls.app.test_client()
