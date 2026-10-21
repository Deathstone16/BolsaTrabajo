"""Aplica límites de archivo mientras Django recibe los chunks multipart."""

from django.core.files.uploadhandler import FileUploadHandler, StopUpload


class BoundedUploadHandler(FileUploadHandler):
    request_limit = 8 * 1024 * 1024
    limits = {
        'cv': 5 * 1024 * 1024,
        'foto': 2 * 1024 * 1024,
        'logo': 2 * 1024 * 1024,
        'banner': 5 * 1024 * 1024,
    }

    def new_file(self, *args, **kwargs):
        super().new_file(*args, **kwargs)
        self.total = 0
        self.limit = self.limits.get(self.field_name, 8 * 1024 * 1024)

    def receive_data_chunk(self, raw_data, start):
        self.total += len(raw_data)
        request_total = getattr(self.request, '_bounded_upload_total', 0) + len(raw_data)
        self.request._bounded_upload_total = request_total
        if self.total > self.limit or request_total > self.request_limit:
            self.request._upload_limit_exceeded = self.field_name
            raise StopUpload(connection_reset=False)
        return raw_data

    def file_complete(self, file_size):
        return None
