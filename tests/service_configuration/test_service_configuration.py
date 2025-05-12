from unittest.mock import create_autospec, patch
from assemblyline.common.importing import load_module_by_path
import os

from assemblyline.odm.messages.task import FileInfo
from assemblyline.odm.models.file import URIInfo
from assemblyline_service_utilities.testing.helper import TestHelper
from assemblyline_v4_service.common.request import ServiceRequest
from assemblyline_v4_service.common.task import Task
import yaml

# from urldownloader import URLDownloader
os.chdir(os.path.join(os.path.dirname(__file__), "../.."))
service_class = load_module_by_path("urldownloader.URLDownloader", ".")


@patch("urldownloader.subprocess.run")
def test_service_conf_custom(mock_run):
    ud = service_class()
    mock_request = create_autospec(ServiceRequest)
    mock_request.file_name = "testfile1"
    mock_request.file_type = "uri/http"
    mock_request.task = create_autospec(Task)

    mock_request.task.fileinfo = create_autospec(FileInfo)
    mock_request.task.fileinfo.uri_info = URIInfo(
        {
            "uri": "http://test.test.not_real",
            "scheme": "http",
            "netloc": "http://test.test.not_real",
            "hostname": "test.test.not_real",
        }
    )

    def get_param(name):
        params = {"proxy": "no_proxy"}
        return params.get(name, None)

    mock_request.get_param = get_param

    # Default should be run when no task param set for uri
    try:
        ud.execute_kangooroo(mock_request, {}, {})
    except Exception:
        pass

    # check parameter values that gets passed to Kangoorooo
    run_args = mock_run.call_args.args[0]
    conf_file_path = run_args[3]
    browser_setting_type = run_args[8]

    assert browser_setting_type == "DEFAULT"

    with open(conf_file_path, "r") as tmp_conf_file:
        conf_file_data = yaml.safe_load(tmp_conf_file)
        assert (
            ud.config.get("default_browser_settings", None)["user_agent"]
            == conf_file_data["browser_settings"]["DEFAULT"]["user_agent"]
        )

        assert (
            ud.config.get("default_browser_settings", None)["window_size"]
            == conf_file_data["browser_settings"]["DEFAULT"]["window_size"]
        )

    os.remove(conf_file_path)

    test_header = {"keyA": "keyB"}
    test_browser_setting = {"window_size": "0x0"}

    # Custom should be run with new custom headings.
    try:
        ud.execute_kangooroo(mock_request, test_header, test_browser_setting)
    except Exception:
        pass

    run_args = mock_run.call_args.args[0]
    conf_file_path = run_args[3]
    browser_setting_type = run_args[8]

    assert browser_setting_type == "CUSTOM"

    with open(conf_file_path, "r") as tmp_conf_file:
        conf_file_data = yaml.safe_load(tmp_conf_file)
        assert (
            ud.config.get("default_browser_settings", None)["user_agent"]
            == conf_file_data["browser_settings"]["DEFAULT"]["user_agent"]
        )

        assert (
            ud.config.get("default_browser_settings", None)["window_size"]
            == conf_file_data["browser_settings"]["DEFAULT"]["window_size"]
        )

        assert conf_file_data["browser_settings"]["CUSTOM"]
        assert "user_agent" not in conf_file_data["browser_settings"]["CUSTOM"]
        assert conf_file_data["browser_settings"]["CUSTOM"]["request_headers"]
        assert conf_file_data["browser_settings"]["CUSTOM"]["request_headers"]["keyA"] == "keyB"
        assert conf_file_data["browser_settings"]["CUSTOM"]["window_size"] == "0x0"

    os.remove(conf_file_path)


@patch("urldownloader.subprocess.run")
def test_service_conf_default(mock_run):

    service_default_user_agent = "DEFAULT_USER_AGENT"
    user_custom_window_size = "CUSTOM_WINDOW_SIZE"

    ud = service_class(config={"default_browser_settings": {"user_agent": service_default_user_agent}})

    mock_request = create_autospec(ServiceRequest)
    mock_request.file_name = "testfile1"
    mock_request.file_type = "uri/http"
    mock_request.task = create_autospec(Task)

    mock_request.task.fileinfo = create_autospec(FileInfo)
    mock_request.task.fileinfo.uri_info = URIInfo(
        {
            "uri": "http://test.test.not_real",
            "scheme": "http",
            "netloc": "http://test.test.not_real",
            "hostname": "test.test.not_real",
        }
    )

    def get_param(name):
        params = {"proxy": "no_proxy"}
        return params.get(name, None)

    mock_request.get_param = get_param

    # Default should be run when no task param set for uri
    try:
        ud.execute_kangooroo(mock_request, {}, {"window_size": user_custom_window_size})
    except Exception:
        pass

    # check parameter values that gets passed to Kangoorooo
    run_args = mock_run.call_args.args[0]
    conf_file_path = run_args[3]
    browser_setting_type = run_args[8]

    assert browser_setting_type == "CUSTOM"

    with open(conf_file_path, "r") as tmp_conf_file:
        conf_file_data = yaml.safe_load(tmp_conf_file)
        assert service_default_user_agent == conf_file_data["browser_settings"]["DEFAULT"]["user_agent"]

        assert user_custom_window_size == conf_file_data["browser_settings"]["CUSTOM"]["window_size"]

    os.remove(conf_file_path)
