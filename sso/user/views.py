from django.contrib.auth import get_user_model

from rest_framework import mixins, permissions, viewsets, status
from rest_framework.response import Response

from oauth2_provider.contrib.rest_framework import TokenHasScope

from .serializers import UserSerializer


class UserRetrieveViewSet(mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user


class UserIntrospectViewSet(mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    permission_classes = [permissions.IsAuthenticated, TokenHasScope]
    required_scopes = ['introspection']
    serializer_class = UserSerializer

    def retrieve(self, request):
        email = request.GET.get('email', None)
        ref = request.GET.get('ref', None)

        User = get_user_model()

        if not email and not ref:
            return Response(status=status.HTTP_400_BAD_REQUEST)

        if email:
            try:
                selected_user = User.objects.get_by_email(email)
            except User.DoesNotExist:
                return Response(status=status.HTTP_404_NOT_FOUND)
        else:
            try:
                selected_user = User.objects.get(account_ref=ref)
            except User.DoesNotExist:
                return Response(status=status.HTTP_404_NOT_FOUND)

        if not selected_user.can_access(request.auth.application):
            # The user does not have permission to access this OAuth2 application
            return Response(status=status.HTTP_404_NOT_FOUND)

        serializer = UserSerializer(selected_user, context=dict(request=request))
        return Response(serializer.data, status=status.HTTP_200_OK)

