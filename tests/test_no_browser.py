import os
import tempfile
from unittest.mock import patch

import pytest
from assemblyline.common.file import make_uri_file
from assemblyline.common.importing import load_module_by_path
from assemblyline_service_utilities.testing.helper import TestHelper
from assemblyline_v4_service.common.request import ServiceRequest
from assemblyline_v4_service.common.task import Task

import urldownloader.urldownloader

service_class = load_module_by_path(
    "urldownloader.urldownloader.URLDownloader", os.path.join(os.path.dirname(__file__), "..")
)
TH = TestHelper(service_class, None)


@pytest.mark.parametrize(
    "no_browser, force_requests",
    [
        (None, None),
        (None, False),
        (None, True),
        (False, None),
        (True, None),
        (False, False),
        (False, True),
        (True, False),
        (True, True),
    ],
)
def test_no_browser(no_browser, force_requests):
    with (
        tempfile.TemporaryDirectory() as temp_dir,
        patch.object(urldownloader.urldownloader.URLDownloader, "execute_kangooroo") as mock_kangooroo,
        patch.object(urldownloader.urldownloader.URLDownloader, "send_http_request") as mock_http_request,
    ):
        file_path = make_uri_file(temp_dir, "https://cybercentrecanada.github.io/assemblyline4_docs/")
        task = Task(TH._create_service_task(file_path, None))
        if force_requests is not None:
            task.service_config["force_requests"] = force_requests  # Set the old parameter for backward checking.
        if no_browser is not None:
            task.service_config["no_browser"] = no_browser  # Set the new parameter for backward checking.
        service_request = ServiceRequest(task)
        service_request._file_path = file_path

        cls = urldownloader.urldownloader.URLDownloader()
        try:
            cls.execute(request=service_request)
        except Exception:
            pass

        if no_browser or force_requests:
            mock_kangooroo.assert_not_called()
            mock_http_request.assert_called_once()
        else:
            mock_kangooroo.assert_called_once()
            mock_http_request.assert_not_called()
