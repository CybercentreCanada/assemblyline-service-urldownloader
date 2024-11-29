import os
import tempfile
from unittest.mock import create_autospec

from assemblyline.common.file import make_uri_file
from assemblyline.common.identify import uri_ident
from assemblyline.odm.messages.task import FileInfo
from assemblyline.odm.models.file import URIInfo
from assemblyline_v4_service.common.request import ServiceRequest
from assemblyline_v4_service.common.result import Result
from assemblyline_v4_service.common.task import Task
from bs4 import BeautifulSoup

from urldownloader import detect_open_directory


def test_invoiceposs_shop_open_directory():
    # Fetched on 2024-11-15
    # hxxp://invoiceposs[.]shop:9895
    uri_source = "http://website.com:9895"
    file_name = "9df18b3a810195a3c8578537d7e7dbbcc70dba9d02209369dac125ed260133ab"
    file_path = os.path.join(os.path.dirname(__file__), file_name)

    mock_request = create_autospec(ServiceRequest)
    mock_request.file_name = file_name
    mock_request.file_type = "uri/http"
    mock_request.result = Result()
    mock_request.task = create_autospec(Task)
    mock_request.task.fileinfo = create_autospec(FileInfo)
    with tempfile.TemporaryDirectory() as temp_dir:
        uri_file_path = make_uri_file(temp_dir, uri_source)
        uri_info = {}
        uri_ident(uri_file_path, uri_info)
    mock_request.task.fileinfo.uri_info = URIInfo(uri_info["uri_info"])

    with open(file_path, "rb") as f:
        data = f.read()
    soup = BeautifulSoup(data, features="lxml")

    detect_open_directory(mock_request, soup)
    assert len(mock_request.result.sections) == 1
    section = mock_request.result.sections[0]
    assert "open directory" in section.title_text.lower()
    assert section.body.startswith("Files:\nhttp://website.com:9895/bab.zip")
    assert "Folders:\nhttp://website.com:9895/ESAYBSA_YSA830246738229/" in section.body


def test_debian_open_directory():
    # Fetched on 2024-11-21
    uri_source = "http://debian.xfree.com.ar/debian-cd/"
    file_name = "519c5a7c047293a5ca84e79c0e45d59ccd85501066bab18006c3b0e6a65aa414"
    file_path = os.path.join(os.path.dirname(__file__), file_name)

    mock_request = create_autospec(ServiceRequest)
    mock_request.file_name = file_name
    mock_request.file_type = "uri/http"
    mock_request.result = Result()
    mock_request.task = create_autospec(Task)
    mock_request.task.fileinfo = create_autospec(FileInfo)
    with tempfile.TemporaryDirectory() as temp_dir:
        uri_file_path = make_uri_file(temp_dir, uri_source)
        uri_info = {}
        uri_ident(uri_file_path, uri_info)
    mock_request.task.fileinfo.uri_info = URIInfo(uri_info["uri_info"])

    with open(file_path, "rb") as f:
        data = f.read()
    soup = BeautifulSoup(data, features="lxml")

    detect_open_directory(mock_request, soup)
    assert len(mock_request.result.sections) == 1
    section = mock_request.result.sections[0]
    assert "open directory" in section.title_text.lower()
    assert section.body == (
        "File:\n"
        "http://debian.xfree.com.ar/debian-cd/ls-lR.gz\n"
        "Folders:\n"
        "http://debian.xfree.com.ar/debian-cd/12.8.0-live/\n"
        "http://debian.xfree.com.ar/debian-cd/12.8.0/\n"
        "http://debian.xfree.com.ar/debian-cd/current-live/\n"
        "http://debian.xfree.com.ar/debian-cd/current/\n"
        "http://debian.xfree.com.ar/debian-cd/project/"
    )


def test_debian_current_open_directory():
    # Fetched on 2024-11-29
    uri_source = "http://debian.xfree.com.ar/debian-cd/current"
    file_name = "e28e7f44cec6d6a752115bd2cb9d50342656c7e8e6442c4c76a0b24a50d4f365"
    file_path = os.path.join(os.path.dirname(__file__), file_name)

    mock_request = create_autospec(ServiceRequest)
    mock_request.file_name = file_name
    mock_request.file_type = "uri/http"
    mock_request.result = Result()
    mock_request.task = create_autospec(Task)
    mock_request.task.fileinfo = create_autospec(FileInfo)
    mock_request.task.fileinfo.uri_info = create_autospec(URIInfo)
    with tempfile.TemporaryDirectory() as temp_dir:
        uri_file_path = make_uri_file(temp_dir, uri_source)
        uri_info = {}
        uri_ident(uri_file_path, uri_info)
    mock_request.task.fileinfo.uri_info = URIInfo(uri_info["uri_info"])

    with open(file_path, "rb") as f:
        data = f.read()
    soup = BeautifulSoup(data, features="lxml")

    detect_open_directory(mock_request, soup)
    assert len(mock_request.result.sections) == 1
    section = mock_request.result.sections[0]
    assert "open directory" in section.title_text.lower()
    assert section.body == (
        "Folders:\n"
        "http://debian.xfree.com.ar/debian-cd/current/amd64/\n"
        "http://debian.xfree.com.ar/debian-cd/current/arm64/\n"
        "http://debian.xfree.com.ar/debian-cd/current/armel/\n"
        "http://debian.xfree.com.ar/debian-cd/current/armhf/\n"
        "http://debian.xfree.com.ar/debian-cd/current/i386/\n"
        "http://debian.xfree.com.ar/debian-cd/current/mips64el/\n"
        "http://debian.xfree.com.ar/debian-cd/current/mipsel/\n"
        "http://debian.xfree.com.ar/debian-cd/current/ppc64el/\n"
        "http://debian.xfree.com.ar/debian-cd/current/s390x/\n"
        "http://debian.xfree.com.ar/debian-cd/current/source/\n"
        "http://debian.xfree.com.ar/debian-cd/current/trace/"
    )


def test_WsgiDAV_open_directory():
    # Fetched on 2024-11-29
    # hxxp://prtmscaup[.]click:7567/EBSYA93840BNVADSFA/
    uri_source = "http://website.com:7567/EBSYA93840BNVADSFA/"
    file_name = "b2f6e108ae0ed41945c6484515e2d7f0ab0daa28eebf66ef0e0b6b133ea50772"
    file_path = os.path.join(os.path.dirname(__file__), file_name)

    mock_request = create_autospec(ServiceRequest)
    mock_request.file_name = file_name
    mock_request.file_type = "uri/http"
    mock_request.result = Result()
    mock_request.task = create_autospec(Task)
    mock_request.task.fileinfo = create_autospec(FileInfo)
    with tempfile.TemporaryDirectory() as temp_dir:
        uri_file_path = make_uri_file(temp_dir, uri_source)
        uri_info = {}
        uri_ident(uri_file_path, uri_info)
    mock_request.task.fileinfo.uri_info = URIInfo(uri_info["uri_info"])

    with open(file_path, "rb") as f:
        data = f.read()
    soup = BeautifulSoup(data, features="lxml")

    detect_open_directory(mock_request, soup)
    assert len(mock_request.result.sections) == 1
    section = mock_request.result.sections[0]
    assert "open directory" in section.title_text.lower()
    assert section.body == "File:\nhttp://website.com:7567/EBSYA93840BNVADSFA/EBSYA93840BNVADSFA_pdf.lnk"
