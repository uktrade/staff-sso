from functools import reduce
from operator import or_

from django.contrib.auth import get_user_model
import django_filters
from django.db.models import Q
from django_filters.rest_framework import DjangoFilterBackend, FilterSet

from oauth2_provider.contrib.rest_framework import TokenHasScope
from rest_framework import mixins, permissions, status, viewsets
from rest_framework.filters import OrderingFilter
from rest_framework.response import Response

from sso.oauth2.models import Application as OAuthApplication
from .serializers import (
    UserSerializer,
    UserParamSerializer,
    UserDetailsSerializer,
    UserListSerializer
)
from .models import User
from .autocomplete import AutocompleteFilter


class UserRetrieveViewSet(mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user

    def partial_update(self, request):
        serializer = UserDetailsSerializer(data=request.data)

        if serializer.is_valid(raise_exception=True):
            try:
                self.update_details(serializer.data)
            except User.DoesNotExist:
                return Response(status=status.HTTP_404_NOT_FOUND)

        return Response(status=status.HTTP_200_OK)

    def update_details(self, data):
        my_user_id = self.request.user.user_id

        user = User.objects.get(user_id=my_user_id)

        for field, value in data.items():
            if value:
                setattr(user, field, value)

        user.save()


class UserIntrospectViewSet(mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    permission_classes = [permissions.IsAuthenticated, TokenHasScope]
    required_scopes = ['introspection']
    serializer_class = UserSerializer

    def retrieve(self, request):

        User = get_user_model()

        serializer = UserParamSerializer(data=request.query_params)
        if serializer.is_valid(raise_exception=True):
            try:
                if serializer.validated_data['email']:
                    selected_user = User.objects.get_by_email(serializer.validated_data['email'])
                elif serializer.validated_data['user_id']:
                    selected_user = User.objects.get(user_id=serializer.validated_data['user_id'])
                else:
                    selected_user = User.objects.get(email_id=serializer.validated_data['email_id'])
            except User.DoesNotExist:
                return Response(status=status.HTTP_404_NOT_FOUND)

        if not selected_user.can_access(request.auth.application):
            # The user does not have permission to access this OAuth2 application
            return Response(status=status.HTTP_404_NOT_FOUND)

        serializer = UserSerializer(selected_user, context=dict(request=request))
        return Response(serializer.data, status=status.HTTP_200_OK)


class UserAutoCompleteFilter(FilterSet):

    autocomplete = AutocompleteFilter(
        search_fields=('first_name', 'last_name'),
    )

    class Meta:
        model = get_user_model()
        fields = {
            'first_name': ('exact', 'icontains'),
            'last_name': ('exact', 'icontains'),
        }


class UserListViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    permission_classes = [permissions.IsAuthenticated, TokenHasScope]
    required_scopes = ['search']
    serializer_class = UserListSerializer

    User = get_user_model()
    queryset = User.objects.all()
    filter_backends = (
        DjangoFilterBackend,
        OrderingFilter,
    )
    filterset_class = UserAutoCompleteFilter
    ordering_fields = ('first_name', 'last_name')
    _default_ordering = ('first_name', 'last_name')

    def _allowed_by_email_suffix_qs(self, application):
        return reduce(
                or_,
                (
                    Q(('emails__email__icontains', domain))
                    for domain in application.allow_access_by_email_suffix.split(',')
                ),
            )

    def _oauth_filtered_qs(self, queryset, application):
        """
        returns filtered queryset based on application
        retrieves all users with allowed email domains, if relevant setting was on
        retrieves users if this application is within thier permitted applications
        retrieves users if user's access profile allows this application
        """
        permitted_qs = queryset.filter(permitted_applications=application)
        access_qs = queryset.filter(access_profiles__oauth2_applications=application)
        if application.allow_access_by_email_suffix:
            email_qs = queryset.filter(self._allowed_by_email_suffix_qs(application))
            qs = email_qs | permitted_qs | access_qs
        else:
            qs = permitted_qs | access_qs
        return qs.distinct()    # remove dups        

    def get_queryset(self):
        queryset = super().get_queryset()
        application = self.request.auth.application

        if isinstance(application, OAuthApplication):
            if not application.default_access_allowed:
                return self._oauth_filtered_qs(queryset, application)

        return queryset

    def filter_queryset(self, queryset):
        """
        Applies the default ordering when the query set has not already been ordered.

        (The autocomplete filter automatically applies an ordering, hence we only set the
        default ordering when another one has not already been set.)
        """
        filtered_queryset = super().filter_queryset(queryset)

        if not filtered_queryset.ordered:
            return filtered_queryset.order_by(*self._default_ordering)

        return filtered_queryset
