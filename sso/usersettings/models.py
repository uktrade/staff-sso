import json

from django.db import models
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model

UserModel = get_user_model()


class UserSettings(models.Model):
    """This model defines a list of app settings that a specified user_id can access"""

    user = models.ForeignKey(
        UserModel, on_delete=models.CASCADE, null=True, to_field="user_id", blank=False
    )

    app_slug = models.CharField(_("app slug"), max_length=50)

    settings = models.TextField(_("settings"))

    def __str__(self):
        return json.dumps(self.settings)

    @staticmethod
    def is_self_slug(string):
        return string.startswith("@.")

    @staticmethod
    def remove_prefix(string, prefix):
        return string[(len(prefix) + 1) :]

    @staticmethod
    def replace_key(dictionary, key_to_replace, key):
        dictionary[key] = dictionary.pop(key_to_replace)

        return dictionary

    def sanitize_settings(self, settings, key, prefix="self"):
        clean_key = self.remove_prefix(key, prefix) if key != prefix else ""

        return (
            str(self.replace_key(settings, key, clean_key))
            .replace("{", "")
            .replace("}", "")
            .replace("'", "")
        )

    @staticmethod
    def get_app_slug(prefix, auth_app_slug):
        if prefix == "@":
            return auth_app_slug
        else:
            return prefix

    @staticmethod
    def create_new(*args, **kwargs):
        user_settings = UserSettings()

        for field, value in kwargs.items():
            if value:
                setattr(user_settings, field, value)

        return user_settings.save()

    @staticmethod
    def get_settings_dict(**kwargs):
        settings = {}

        for key, value in kwargs.items():
            if value:
                setattr(settings, key, value)

        return settings

    @staticmethod
    def get_app_settings(is_global, blacklist):
        local_settings = {}

        for key, value in is_global[0].items():
            if key not in blacklist["blacklist"]:
                local_settings[key] = value

        return local_settings

    @staticmethod
    def set_settings(user_id, app_slug, settings):
        UserSettings.create_new(user_id=user_id, app_slug=app_slug, settings=settings)

    def get_settings(self, is_global, settings):
        if is_global:
            return self.get_app_settings(settings, blacklist=["global"])
        else:
            return settings

    @staticmethod
    def get_user_permissions_tuple(user_permissions):
        return [(permission.id, permission.name) for permission in user_permissions]

    @staticmethod
    def is_user_allowed_to(permission, user_permissions):
        return any([permission in item for item in user_permissions])

    @staticmethod
    def get_filter_params(data, request, user_settings):
        key = list(data.keys())[0]
        prefix = str(key.split(".")[0])
        auth_app_slug = request.auth.application.name
        slug = user_settings.get_app_slug(prefix, auth_app_slug)
        clean_key = user_settings.remove_prefix(key, prefix)

        return clean_key, slug, key, prefix

    @staticmethod
    def get_dot_notation(data):
        """
        Recursively transforms JSON format {"dot": {"notation": {"item": "one"}, {"item": "two"}}}
        into [{'dot.notation.item:one'}, {'dot.notation.item:two'}]
        :param data - JSON dictionary from the request
        :return a list of single pair dictionaries
        """
        items_list = []

        def transform_item(value, slug=""):
            if value and isinstance(value, dict):
                for key in value.keys():
                    transform_item(value[key], slug + "." + str(key))
            else:
                val = str(value) if value else ""
                items_list.append({slug[1:]: val})

        transform_item(data)
        return items_list

    @staticmethod
    def build_json(item):
        """
        Recursively transforms dot notation string format 'dot.notation.item:one'
        into {"dot": {"notation": {"item": "one"}}}
        :param item - dot notation string from the the queryset
        :return a dictionary with a single parent
        """

        def branch(tree, vector, value):
            if isinstance(value, str):
                value = value.strip()

                if value.lower() in ["true", "false"]:
                    value = True if value.lower() == "true" else False

            key = vector[0]

            tree.update(
                {
                    key: value
                    if len(vector) == 1
                    else branch(tree[key] if key in tree else {}, vector[1:], value)
                }
            )

            return tree

        row_dict = {}
        for colName, rowValue in item.items():
            row_dict.update(branch(row_dict, colName.split("."), rowValue))

        return row_dict

    def merge(self, a, b, path=[]):
        """
        Recursively merges dictionary b into dictionary a
        """

        for key in b:
            if key in a:
                if isinstance(a[key], dict) and isinstance(b[key], dict):
                    self.merge(a[key], b[key], path + [str(key)])
                elif a[key] == b[key]:
                    pass
                else:
                    raise ValueError("Conflict at %s" % ".".join(path + [str(key)]))

            else:
                a[key] = b[key]
        return a

    def get_json_data(self, all_settings):
        data = {}

        for item in all_settings:
            arr = str(item).split(":")
            clone_data = data
            new_data = self.build_json({arr[0]: arr[1]})
            data = self.merge(clone_data, new_data)

        return data

    @staticmethod
    def get_all_settings(request, user_id, auth_app_slug, user_can_access_all_settings=False):
        all_settings = []

        if user_can_access_all_settings and "match_all" in request.data:
            raw_settings = UserSettings.objects.filter(user_id=user_id).values(
                "app_slug", "settings"
            )
            for it in raw_settings:
                all_settings.append(str(it["app_slug"] + "." + it["settings"]))
        else:
            specific_app_settings = [
                auth_app_slug + "." + str(item).replace('"', "")
                for item in UserSettings.objects.filter(user_id=user_id, app_slug=auth_app_slug)
            ]

            global_settings = [
                "global." + str(item).replace('"', "")
                for item in UserSettings.objects.filter(user_id=user_id, app_slug="global")
            ]

            all_settings = global_settings + specific_app_settings

        return all_settings
