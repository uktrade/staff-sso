import re
from functools import reduce
from operator import or_

from django.db.models import Q
from django_filters import CharFilter


class AutocompleteFilter(CharFilter):
    """
    Autocomplete filters that performs a prefix match of the specified search terms against a
    set of fields.

    See the docstring for _apply_autocomplete_filter_to_queryset below for more details on how
    it operates.
    """

    def __init__(self, *args, search_fields=None, **kwargs):
        """
        Initialises the filter.

        The search_fields keyword argument specifies which fields to search and is required.
        """
        if search_fields is None:
            raise ValueError('The search_fields keyword argument must be specified')

        self.search_fields = search_fields
        super().__init__(*args, **kwargs)

    def filter(self, queryset, value):
        """Filters the queryset."""
        # This gets called even if the query parameter is not in the query string. So do nothing
        # if the query string was not specified
        if self.field_name not in self.parent.form.data:
            return queryset

        return _apply_autocomplete_filter_to_queryset(queryset, self.search_fields, value)


def _apply_autocomplete_filter_to_queryset(queryset, autocomplete_fields, search_string):
    """
    Performs an autocomplete search.

    search_string is split into tokens. Each token must match a prefix of a word in any of
    the following fields (case-insensitive) in any of the fields specified in autocomplete_fields.

    A word is defined as an unbroken sequence of letters, numbers and/or underscores.

    Results are automatically ordered as follows:

      - the fields in autocomplete_fields (in order)
      - and finally pk (so that the results are deterministic if the other ordering fields are
        identical)
    """
    escaped_tokens = [re.escape(token) for token in search_string.split()]

    # Skip the remainder of the logic if an empty string or only spaces were entered
    if not escaped_tokens:
        return queryset.order_by(
            *autocomplete_fields,
            'pk',
        )

    filter_q_objects_for_tokens = (
        _make_filter_q_for_token(autocomplete_fields, escaped_token)
        for escaped_token in escaped_tokens
    )

    return queryset.filter(
        *filter_q_objects_for_tokens,
    ).order_by(
        *autocomplete_fields,
        'pk',
    )

def _make_filter_q_for_token(fields, escaped_token):
    r"""
    Creates a Q object that checks if a token appears in a list of fields (as a prefix).

    For example::

        _make_filter_q_for_token(['first_name', 'last_name'], 'Joh')

    would return a Q object equivalent to::

        Q(first_name__iregex='\mJoh') | Q(last_name__iregex='\mJoh')
    """
    return reduce(
        or_,
        (
            Q(_make_prefix_match_q(field, escaped_token))
            for field in fields
        ),
    )


def _make_prefix_match_q(field, escaped_token):
    r"""
    Generates a Q object that performs a case-insensitive match of a token with prefixes
    of any of the words in a field.

    The \m in the regular expression means a word boundary (a word is defined as a unbroken
    sequence of letters, numbers and underscores). As the escaped token follows \m,
    the token must match the beginning of any of the words in the specified field.
    """
    q_kwargs = {
        f'{field}__iregex': rf'\m{escaped_token}',
    }
    return Q(**q_kwargs)
