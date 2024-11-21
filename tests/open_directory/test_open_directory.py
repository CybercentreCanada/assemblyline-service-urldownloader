import os
from unittest.mock import create_autospec

from assemblyline.odm.messages.task import FileInfo
from assemblyline.odm.models.file import URIInfo
from assemblyline_v4_service.common.request import ServiceRequest
from assemblyline_v4_service.common.result import Result
from assemblyline_v4_service.common.task import Task
from bs4 import BeautifulSoup

from urldownloader import detect_open_directory


def test_invoiceposs_shop_open_directory():
    uri_source = "http://invoiceposs.shop:9895"
    # Fetched on 2024-11-15
    file_name = "9df18b3a810195a3c8578537d7e7dbbcc70dba9d02209369dac125ed260133ab"
    file_path = os.path.join(os.path.dirname(__file__), file_name)

    mock_request = create_autospec(ServiceRequest)
    mock_request.file_name = file_name
    mock_request.file_type = "code/html"
    mock_request.result = Result()
    mock_request.task = create_autospec(Task)
    mock_request.task.fileinfo = create_autospec(FileInfo)
    mock_request.task.fileinfo.uri_info = create_autospec(URIInfo)
    mock_request.task.fileinfo.uri_info.uri = uri_source

    with open(file_path, "rb") as f:
        data = f.read()
    soup = BeautifulSoup(data, features="lxml")

    detect_open_directory(mock_request, soup)
    assert len(mock_request.result.sections) == 1
    section = mock_request.result.sections[0]
    assert "open directory" in section.title_text.lower()
    assert section.body.startswith("Files:\nhttp://invoiceposs.shop:9895/bab.zip")
    assert "Folders:\nhttp://invoiceposs.shop:9895/ESAYBSA_YSA830246738229/" in section.body


def test_debian_open_directory():
    uri_source = "http://debian.xfree.com.ar/debian-cd/"
    # Fetched on 2024-11-21
    file_name = "519c5a7c047293a5ca84e79c0e45d59ccd85501066bab18006c3b0e6a65aa414"
    file_path = os.path.join(os.path.dirname(__file__), file_name)

    mock_request = create_autospec(ServiceRequest)
    mock_request.file_name = file_name
    mock_request.file_type = "code/html"
    mock_request.result = Result()
    mock_request.task = create_autospec(Task)
    mock_request.task.fileinfo = create_autospec(FileInfo)
    mock_request.task.fileinfo.uri_info = create_autospec(URIInfo)
    mock_request.task.fileinfo.uri_info.uri = uri_source

    with open(file_path, "rb") as f:
        data = f.read()
    soup = BeautifulSoup(data, features="lxml")

    detect_open_directory(mock_request, soup)
    assert len(mock_request.result.sections) == 1
    section = mock_request.result.sections[0]
    assert "open directory" in section.title_text.lower()
    assert section.body.startswith("File:\nhttp://debian.xfree.com.ar/debian-cd/ls-lR.gz")
    assert "Folders:\nhttp://debian.xfree.com.ar/debian-cd/12.8.0-live/" in section.body
