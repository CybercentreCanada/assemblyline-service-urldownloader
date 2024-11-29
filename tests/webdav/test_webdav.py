import os
from unittest.mock import create_autospec

from assemblyline.odm.messages.task import FileInfo
from assemblyline.odm.models.file import URIInfo
from assemblyline_v4_service.common.request import ServiceRequest
from assemblyline_v4_service.common.result import Result
from assemblyline_v4_service.common.task import Task

from urldownloader import detect_webdav_listing


def test_webdav_Downloads():
    # Fetched on 2024-11-27
    # hxxp://87[.]120[.]115.[.]240/Downloads"
    uri_source = "http://1.1.1.1/Downloads"
    file_name = "57dbb207a1222abf0990054635f2d4315dfa7b8be898d5b8cfd40de9ef16023a"
    file_path = os.path.join(os.path.dirname(__file__), file_name)

    mock_request = create_autospec(ServiceRequest)
    mock_request.file_name = file_name
    mock_request.file_type = "uri/http"
    mock_request.result = Result()
    mock_request.task = create_autospec(Task)
    mock_request.task.fileinfo = create_autospec(FileInfo)
    mock_request.task.fileinfo.uri_info = create_autospec(URIInfo)
    mock_request.task.fileinfo.uri_info.uri = uri_source

    with open(file_path, "rb") as f:
        data = f.read()

    detect_webdav_listing(mock_request, data)
    assert len(mock_request.result.sections) == 1
    section = mock_request.result.sections[0]
    assert "webdav" in section.title_text.lower()
    assert section.body.startswith(
        "http://1.1.1.1/Downloads/\nhttp://1.1.1.1/Downloads/9160fb03d89ec42b78b47dab53e8b275.jpeg.lnk"
    )
    assert "http://1.1.1.1/Downloads/12375_depression-anger-attacks.pdf.lnk" in section.body
