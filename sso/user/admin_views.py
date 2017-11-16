import csv

from django.contrib.auth import get_user_model
from django.contrib.admin.views.decorators import staff_member_required
from django.http.response import StreamingHttpResponse


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

