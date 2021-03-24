import json

from django.http import HttpResponse
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import UserSettings
from .serializers import UserSettingsSerializer


class UserSettingsListView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = UserSettingsSerializer

    def post(self, request):
        """
        Prefix is used to get the corresponding app slug.
        If the prefix is `@.` then it's the application in the session
        If the prefix is `global.` then this data can be accessed from any application
        """
        user_settings = UserSettings()
        raw_data = request.data
        settings_list = user_settings.get_dot_notation(raw_data)
        user_id = request.user.user_id

        for data in settings_list:
            clean_key, slug, key, prefix = user_settings.get_filter_params(
                data, request, user_settings
            )

            settings = UserSettings.sanitize_settings(user_settings, data, key, prefix)

            try:
                """
                Update existing record
                """
                UserSettings.objects.get(
                    user_id=user_id, app_slug=slug, settings__startswith=clean_key
                )

                existing_record = UserSettings.objects.filter(
                    user_id=user_id, app_slug=slug, settings__startswith=clean_key
                )

                if len(existing_record) and len(existing_record) <= 1:
                    first_record = existing_record.first()
                    first_record.settings = settings
                    first_record.save()
                else:
                    return Response(status=status.HTTP_300_MULTIPLE_CHOICES)

            except UserSettings.DoesNotExist:
                all_settings = user_settings.get_all_settings(request, user_id, slug)
                new_settings = slug + "." + settings
                all_settings.append(new_settings)

                try:
                    """
                    Backtest if the new setting fits the existing data.
                    If it doesn't fit then it will raise a `conflict` exception in the
                    method which merges the atomic settings together in the json output
                    """
                    user_settings.get_json_data(all_settings)

                except ValueError:
                    return Response(status=status.HTTP_400_BAD_REQUEST)

                """
                Then create the new record
                """
                UserSettings.set_settings(user_id=user_id, app_slug=slug, settings=settings)

        return Response(status=status.HTTP_200_OK)

    @staticmethod
    def delete(request):
        """
        If match_all in request body, then delete all settings for the `me` user
        """
        user_settings = UserSettings()
        raw_data = request.data
        user_id = request.user.user_id

        settings_list = user_settings.get_dot_notation(raw_data)

        for data in settings_list:
            clean_key, slug, key, prefix = user_settings.get_filter_params(
                data, request, user_settings
            )

        try:
            recorded_settings = UserSettings.objects.filter(
                user_id=user_id, app_slug=slug, settings__startswith=clean_key
            )

            if recorded_settings:
                recorded_settings.delete()
            else:
                raise UserSettings.DoesNotExist

        except UserSettings.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        return Response(status=status.HTTP_204_NO_CONTENT)

    @staticmethod
    def get(request):
        """
        If match_all in request body, then retrieve all settings for the `me` user
        """
        user_settings = UserSettings()
        user_id = request.user.user_id
        auth_app_slug = request.auth.application.name
        can_view_all_user_settings = request.auth.application.can_view_all_user_settings

        all_settings = user_settings.get_all_settings(
            request, user_id, auth_app_slug, can_view_all_user_settings
        )
        json_data = user_settings.get_json_data(all_settings)

        return HttpResponse(content=json.dumps(json_data, indent=4), status=status.HTTP_200_OK)
