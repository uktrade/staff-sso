import csv
from io import StringIO

from django.contrib.auth import get_user_model
from django.contrib.admin.views.decorators import staff_member_required
from django.http.response import StreamingHttpResponse
from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.views.generic import FormView

from .data_import import UserImport
from .forms import AdminUserUploadForm


class Echo(object):
    """An object that implements just the write method of the file-like
    interface.
    """
    def write(self, value):
        """Write the value by returning it, instead of storing in a buffer."""
        return value


def get_user_csv_data():
    User = get_user_model()

    for user in User.objects.all().order_by('email'):
        row = [user.email, user.first_name, user.last_name]

        row.extend(user.emails.exclude(email=user.email).values_list('email', flat=True))

        yield row


@staff_member_required
def download_user_csv(request):
    """A temporary CSV download view"""

    pseudo_buffer = Echo()
    writer = csv.writer(pseudo_buffer)
    response = StreamingHttpResponse((writer.writerow(row) for row in get_user_csv_data()),
                                     content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename=\'user_download.csv\''
    return response


@method_decorator(staff_member_required, name='dispatch')
class AdminUserImportView(FormView):
    form_class = AdminUserUploadForm
    template_name = 'admin/user-import.html'

    def form_valid(self, form):

        data = form.cleaned_data['file'].read()

        # this may be too presumptious?
        stream = StringIO(data.decode('UTF-8'))

        csv_reader = csv.reader(stream)

        user_import = UserImport(csv_reader, form.cleaned_data['applications'])
        user_import.process(dry_run=form.cleaned_data['dry_run'])

        return render(
            self.request,
            'admin/user-import.html',
            {
                'status': user_import.logs,
                'form': self.get_form()
            }
        )
