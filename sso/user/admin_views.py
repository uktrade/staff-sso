import csv
from io import StringIO

from django.contrib.admin.views.decorators import staff_member_required

from django.http.response import StreamingHttpResponse
from django.shortcuts import get_object_or_404, render
from django.utils.decorators import method_decorator
from django.views.generic import FormView
from django.views.generic.base import View

from sso.oauth2.models import Application
from .data_export import UserDataExport, UserPermissionExport
from .data_import import UserAliasImport, UserMergeImport
from .forms import AdminUserAddAliasForm, AdminUserUploadForm
from .models import User


class Echo(object):
    """An object that implements just the write method of the file-like
    interface.
    """
    def write(self, value):
        """Write the value by returning it, instead of storing in a buffer."""
        return value


@method_decorator(staff_member_required, name='dispatch')
class CSVExportView(View):

    class Echo(object):
        """An object that implements just the write method of the file-like
        interface.
        """

        def write(self, value):
            """Write the value by returning it, instead of storing in a buffer."""
            return value

    def __init__(self):
        assert getattr(self, 'generator_object', None)
        assert getattr(self, 'file_name', None)

    def get(self, request, *args, **kwargs):
        pseudo_buffer = self.Echo()
        writer = csv.writer(pseudo_buffer)
        response = StreamingHttpResponse((writer.writerow(row) for row in self.generator_object),
                                         content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename={self.file_name}'
        return response


class UserDataExportView(CSVExportView):
    generator_object = UserDataExport()
    file_name = 'user_data.csv'


class UserPermissionExportView(CSVExportView):
    generator_object = UserPermissionExport()
    file_name = 'user_permission_data.csv'


@method_decorator(staff_member_required, name='dispatch')
class CSVImportView(FormView):
    def form_valid(self, form):

        assert getattr(self, 'import_class', None)

        data = form.cleaned_data['file'].read()

        stream = StringIO(data.decode('UTF-8'))

        csv_reader = csv.reader(stream)

        data_import = self.import_class(csv_reader, form.cleaned_data)
        data_import.process(dry_run=form.cleaned_data['dry_run'])

        return render(
            self.request,
            self.template_name,
            {
                'status': data_import.logs,
                'form': self.get_form()
            }
        )


class AdminUserMergeImportView(CSVImportView):
    form_class = AdminUserUploadForm
    template_name = 'admin/user-import.html'
    import_class = UserMergeImport


class AdminUserAliasAddImportView(CSVImportView):
    form_class = AdminUserAddAliasForm
    template_name = 'admin/user-alias-import.html'
    import_class = UserAliasImport


@method_decorator(staff_member_required, name='dispatch')
class ShowUserPermissionsView(View):

    template_name = 'admin/show-user-permissions.html'

    def get(self, request, *args, **kwargs):
        user = get_object_or_404(User, pk=kwargs['user_id'])

        apps = [{'name': app.name, 'access': user.can_access(app)} for app in Application.objects.all()]

        context = {
            'user': user,
            'applications': apps,
        }

        return render(request, self.template_name, context)
