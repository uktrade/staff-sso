from django.contrib.auth import get_user_model
from django.views.generic.base import View
from django.shortcuts import get_object_or_404, render
from django.http import HttpResponse, Http404

from oauth2_provider.contrib.rest_framework import TokenHasScope
from rest_framework import mixins, permissions, status, viewsets
from rest_framework.response import Response
from rest_framework import generics

from .serializers import UserSerializer, UserParamSerializer, UserDetailsSerializer
from .models import User


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
            except RuntimeError as re:
                raise Http404(re)

        return Response(status=status.HTTP_202_ACCEPTED)

    def update_details(self, data):
        my_user_id = self.request.user.user_id
        first_name = data['first_name']
        last_name = data['last_name']
        contact_email = data['contact_email']

        user = User.objects.get(user_id=my_user_id)

        if contact_email:
            user.contact_email = contact_email

        if first_name:
            user.first_name = first_name

        if last_name:
            user.last_name = last_name

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
                else:
                    selected_user = User.objects.get(user_id=serializer.validated_data['user_id'])
            except User.DoesNotExist:
                return Response(status=status.HTTP_404_NOT_FOUND)

        if not selected_user.can_access(request.auth.application):
            # The user does not have permission to access this OAuth2 application
            return Response(status=status.HTTP_404_NOT_FOUND)

        serializer = UserSerializer(selected_user, context=dict(request=request))
        return Response(serializer.data, status=status.HTTP_200_OK)


