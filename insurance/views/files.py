from django.http import Http404, HttpResponse
from django.views import View

from insurance.models import StoredFile
from insurance.storage import valid_signature


class StoredFileView(View):
    """
    Serves a file kept by DatabaseStorage. No login is needed: the `sig` in the
    URL proves the link came from the API, which only hands it to users allowed
    to see the record the file belongs to.
    """

    def get(self, request, name):
        if not valid_signature(name, request.GET.get('sig')):
            raise Http404
        stored = StoredFile.objects.filter(name=name).first()
        if stored is None:
            raise Http404
        response = HttpResponse(bytes(stored.content), content_type=stored.content_type)
        response['Content-Length'] = stored.size
        # Names are never reused, so a file at a URL never changes
        response['Cache-Control'] = 'private, max-age=86400'
        response['X-Content-Type-Options'] = 'nosniff'
        return response
