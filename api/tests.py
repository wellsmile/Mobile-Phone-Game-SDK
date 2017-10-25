from django.test import TestCase

import uuid
from models import User

class UserTestCase(TestCase):
    def setUp(self):
        user = User(username='testuser100')
        self.userid = uuid.uuid4().hex
        user.id = self.userid
        user.imei = 'imei'
        user.phone = '152104117809'
        user.guid = 'guid'
        user.set_password('password')
        user.save()
        
    def test_user_create(self):
        user = User.objects.get(id=self.userid)
        self.assertEqual(self.userid, user.id, 'User ID is not consistent')
        