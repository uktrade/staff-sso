import json

from datetime import timedelta

import pytest
from django.urls import reverse_lazy
from django.utils import timezone


from sso.usersettings.models import UserSettings

from .factories.oauth import AccessTokenFactory, ApplicationFactory
from .factories.user import UserFactory
from .factories.usersettings import UserSettingsFactory

pytestmark = [
    pytest.mark.django_db
]


def get_oauth_token(expires=None, user=None, scope='read'):

    if not user:
        user = UserFactory(
            email='user1@example.com',
            first_name='John',
            last_name='Doe'
        )

    application = ApplicationFactory(default_access_allowed=True)

    access_token = AccessTokenFactory(
        application=application,
        user=user,
        expires=expires or (timezone.now() + timedelta(days=1)),
        scope=scope
    )

    return user, access_token.token


def get_user_settings(user_settings=None):

    if not user_settings:
        user_settings = UserSettingsFactory()

    return user_settings


def create_settings_batch(user):
    UserSettingsFactory.create_batch(50)
    UserSettingsFactory.create_batch(5, user_id=user.user_id)

    UserSettingsFactory.create(
        user_id=user.user_id,
        app_slug='Test oauth app',
        settings='private_cake.multi_layer.first_layer: base cake'
    )

    UserSettingsFactory.create(
        user_id=user.user_id,
        app_slug='Test oauth app',
        settings='private_cake.multi_layer.second_layer: cream'
    )

    UserSettingsFactory.create(
        user_id=user.user_id,
        app_slug='Test oauth app',
        settings='private_cake.multi_layer.third_layer: middle cake'
    )

    UserSettingsFactory.create(
        user_id=user.user_id,
        app_slug='Test oauth app',
        settings='private_cake.multi_layer.fourth_layer.frosting: whipped_cream'
    )

    UserSettingsFactory.create(
        user_id=user.user_id,
        app_slug='Test oauth app',
        settings='private_cake.multi_layer.fourth_layer.sprinkles: strawberries'
    )


class TestUserSettings:
    MY_USER_SETTINGS_PER_APP_URL = reverse_lazy(
        'api-v1:user-settings:settings_per_app'
    )

    def test_post(self, api_client):
        """
        Test that authenticated users can post settings.
        """
        user, token = get_oauth_token()

        UserSettingsFactory.create_batch(50)
        UserSettingsFactory.create_batch(5, user_id=user.user_id)

        api_client.credentials(HTTP_AUTHORIZATION='Bearer ' + token)
        response = api_client.post('/api/v1/user-settings/', {
            '@': {
                'private_cake': 'Carrot cake'
            },
            'global': {
                'global_cake': 'Coffee and walnut cake'
            }
        }, format='json')

        user_settings = UserSettings.objects.get(user_id=user.user_id, app_slug='Test oauth app')
        user_settings_global = UserSettings.objects.get(user_id=user.user_id, app_slug='global')

        assert response.status_code == 200
        assert getattr(user_settings, 'settings') == 'private_cake: Carrot cake'
        assert getattr(user_settings_global, 'settings') == 'global_cake: Coffee and walnut cake'

    def test_update(self, api_client):
        """
        Test that authenticated users can update settings.
        """
        user, token = get_oauth_token()

        UserSettingsFactory.create_batch(50)
        UserSettingsFactory.create_batch(5, user_id=user.user_id)
        UserSettingsFactory.create(
            user_id=user.user_id,
            app_slug='Test oauth app',
            settings='private_cake: Carrot cake'
        )

        api_client.credentials(HTTP_AUTHORIZATION='Bearer ' + token)
        response = api_client.post('/api/v1/user-settings/', {
            '@': {
                'private_cake': 'Coffee and walnut cake'
            }
        }, format='json')

        user_settings = UserSettings.objects.get(user_id=user.user_id, app_slug='Test oauth app')

        assert response.status_code == 200
        assert getattr(user_settings, 'settings') == 'private_cake: Coffee and walnut cake'

    def test_update_nested_items_incorrectly(self, api_client):
        """
        Test that authenticated users can update nested settings incorrectly
        by passing an dictionary to a single value.
        """
        user, token = get_oauth_token()
        create_settings_batch(user)
        api_client.credentials(HTTP_AUTHORIZATION='Bearer ' + token)

        response_before_update = api_client.get('/api/v1/user-settings/')
        assert response_before_update.status_code == 200
        assert json.loads(response_before_update.content.decode('utf8').replace("'", '"')) == {
          'Test oauth app': {
            'private_cake': {
              'multi_layer': {
                'first_layer': 'base cake',
                'fourth_layer': {
                  'frosting': 'whipped_cream',
                  'sprinkles': 'strawberries'
                },
                'second_layer': 'cream',
                'third_layer': 'middle cake'
              }
            }
          }
        }

        response = api_client.post('/api/v1/user-settings/', {
                '@': {
                    'private_cake': {
                        'multi_layer': {
                            'first_layer': {
                                'support': 'plate'
                            }
                        }
                    }
                }
            }, format='json')

        assert response.status_code == 400

    def test_update_nested_items(self, api_client):
        """
        Test that authenticated users can update nested settings.
        """
        user, token = get_oauth_token()
        create_settings_batch(user)
        api_client.credentials(HTTP_AUTHORIZATION='Bearer ' + token)

        response_before_delete = api_client.get('/api/v1/user-settings/')
        assert response_before_delete.status_code == 200
        assert json.loads(response_before_delete.content.decode('utf8').replace("'", '"')) == {
          'Test oauth app': {
            'private_cake': {
              'multi_layer': {
                'first_layer': 'base cake',
                'fourth_layer': {
                  'frosting': 'whipped_cream',
                  'sprinkles': 'strawberries'
                },
                'second_layer': 'cream',
                'third_layer': 'middle cake'
              }
            }
          }
        }

        response = api_client.post('/api/v1/user-settings/', {
            '@': {
                'private_cake': {
                    'multi_layer': {
                        'first_layer': 'plate',
                        'second_layer': 'pecan',
                    }
                }
            }
        }, format='json')
        assert response.status_code == 200

        response_after_delete = api_client.get('/api/v1/user-settings/')
        assert response_after_delete.status_code == 200
        assert json.loads(response_after_delete.content.decode('utf8').replace("'", '"')) == {
            'Test oauth app': {
                'private_cake': {
                    'multi_layer': {
                        'first_layer': 'plate',  # first_layer updated from `base cake` to `plate`
                        'fourth_layer': {
                            'frosting': 'whipped_cream',
                            'sprinkles': 'strawberries'
                        },
                        'second_layer': 'pecan',
                        'third_layer': 'middle cake'
                    }
                }
            }
        }

    def test_get(self, api_client):
        """
        Test that authenticated users can get settings.
        """
        user, token = get_oauth_token()

        UserSettingsFactory.create_batch(50)
        UserSettingsFactory.create_batch(5, user_id=user.user_id)

        UserSettingsFactory.create(
            user_id=user.user_id,
            app_slug='Test oauth app',
            settings='private_cake: Carrot cake'
        )
        
        UserSettingsFactory.create(
            user_id=user.user_id,
            app_slug='global',
            settings='global_cake: Coffee and walnut cake'
        )

        api_client.credentials(HTTP_AUTHORIZATION='Bearer ' + token)

        response = api_client.get('/api/v1/user-settings/')

        assert response.status_code == 200
        assert json.loads(response.content.decode('utf8').replace("'", '"')) == {
                'Test oauth app': {'private_cake': 'Carrot cake'},
                'global': {'global_cake': 'Coffee and walnut cake'}
            }

    def test_get_all(self, api_client):
        """
        Test that authenticated users can get all settings.
        """
        user, token = get_oauth_token()

        UserSettingsFactory.create_batch(50)
        UserSettingsFactory.create_batch(5, user_id=user.user_id)

        UserSettingsFactory.create(
            user_id=user.user_id,
            app_slug='Test oauth app',
            settings='private_cake: Carrot cake'
        )

        UserSettingsFactory.create(
            user_id=user.user_id,
            app_slug='global',
            settings='global_cake: Coffee and walnut cake'
        )

        api_client.credentials(HTTP_AUTHORIZATION='Bearer ' + token)

        response = api_client.get('/api/v1/user-settings/')

        assert response.status_code == 200
        assert json.loads(response.content.decode('utf8').replace("'", '"')) == {
                'Test oauth app': {'private_cake': 'Carrot cake'},
                'global': {'global_cake': 'Coffee and walnut cake'}
            }

    def test_delete_item(self, api_client):
        """
        Test that authenticated users can delete settings.
        """
        user, token = get_oauth_token()

        UserSettingsFactory.create_batch(50)
        UserSettingsFactory.create_batch(5, user_id=user.user_id)

        UserSettingsFactory.create(
            user_id=user.user_id,
            app_slug='Test oauth app',
            settings='private_cake: Carrot cake'
        )

        UserSettingsFactory.create(
            user_id=user.user_id,
            app_slug='global',
            settings='global_cake: Coffee and walnut cake'
        )

        user_settings_before = UserSettings.objects.get(user_id=user.user_id, app_slug='Test oauth app')

        api_client.credentials(HTTP_AUTHORIZATION='Bearer ' + token)

        response = api_client.delete('/api/v1/user-settings/', {
            '@': {
                'private_cake': {}
            }
        }, format='json')

        try:
            user_settings_after = UserSettings.objects.get(user_id=user.user_id, app_slug='Test oauth app')
        except UserSettings.DoesNotExist:
            user_settings_after = None

        assert response.status_code == 204
        assert user_settings_after is None
        assert getattr(user_settings_before, 'settings') == 'private_cake: Carrot cake'

    def test_delete_nonexistent_item(self, api_client):
        """
        Test that authenticated users can delete settings.
        """
        user, token = get_oauth_token()

        UserSettingsFactory.create_batch(50)
        UserSettingsFactory.create_batch(5, user_id=user.user_id)

        UserSettingsFactory.create(
            user_id=user.user_id,
            app_slug='Test oauth app',
            settings='private_cake: Carrot cake'
        )

        UserSettingsFactory.create(
            user_id=user.user_id,
            app_slug='global',
            settings='global_cake: Coffee and walnut cake'
        )

        api_client.credentials(HTTP_AUTHORIZATION='Bearer ' + token)

        response = api_client.delete('/api/v1/user-settings/', {
            '@': {
                'brick': {}
            }
        }, format='json')

        assert response.status_code == 404

    def test_delete_nested_items(self, api_client):
        """
        Test that authenticated users can delete nested settings.
        """
        user, token = get_oauth_token()
        create_settings_batch(user)
        api_client.credentials(HTTP_AUTHORIZATION='Bearer ' + token)

        response_before_delete = api_client.get('/api/v1/user-settings/')
        assert response_before_delete.status_code == 200
        assert json.loads(response_before_delete.content.decode('utf8').replace("'", '"')) == {
          'Test oauth app': {
            'private_cake': {
              'multi_layer': {
                'first_layer': 'base cake',
                'fourth_layer': {
                  'frosting': 'whipped_cream',
                  'sprinkles': 'strawberries'
                },
                'second_layer': 'cream',
                'third_layer': 'middle cake'
              }
            }
          }
        }

        response = api_client.delete('/api/v1/user-settings/', {
            '@': {
                'private_cake': {
                    'multi_layer': {
                        'fourth_layer': {
                            'sprinkles': {}
                        }
                    }
                }
            }
        }, format='json')
        assert response.status_code == 204

        response_after_delete = api_client.get('/api/v1/user-settings/')
        assert response_after_delete.status_code == 200
        assert json.loads(response_after_delete.content.decode('utf8').replace("'", '"')) == {
            'Test oauth app': {
                'private_cake': {
                    'multi_layer': {
                        'first_layer': 'base cake',
                        'fourth_layer': {
                            'frosting': 'whipped_cream'
                            # strawberry sprinkles are no longer here
                        },
                        'second_layer': 'cream',
                        'third_layer': 'middle cake'
                    }
                }
            }
        }
