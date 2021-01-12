
    def user_deactivation_date(user):
        """Extract the time the user was deactivated from the django admin log"""

        ACTION_TEXT = '[{"changed": {"fields": ["is_active"]}}]'

        user_type = ContentType.objects.get_for_model(user)

        if user.is_active:
            return False

        log_entry = user.logentry_set.filter(
            content_type=user_type,
            action=ACTION_TEXT,
            action_flag=DELETION).order_by('-id')

        return None if not log_entry else log_entry[0].action_time
