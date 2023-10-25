import json
import os
import time

import requests
import yaml
from assemblyline.common.identify import Identify
from assemblyline_service_utilities.common.tag_helper import add_tag
from assemblyline_v4_service.common.base import ServiceBase
from assemblyline_v4_service.common.request import ServiceRequest
from assemblyline_v4_service.common.result import (
    Result,
    ResultImageSection,
    ResultKeyValueSection,
    ResultSection,
    ResultTableSection,
    TableRow,
)
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.options import Options


class URLDownloader(ServiceBase):
    def __init__(self, config) -> None:
        super().__init__(config)
        self.identify = Identify(use_cache=False)
        self.request_timeout = self.config.get("request_timeout", 90)

    def execute(self, request: ServiceRequest) -> None:
        result = Result()
        request.result = result

        with open(request.file_path, "r") as f:
            data = yaml.safe_load(f)

        data.pop("uri")
        headers = data.pop("headers", {})

        verb = data.pop("verb", "GET")
        if verb == "GET":
            if data or headers:
                ignored_params_section = ResultKeyValueSection("Ignored params", parent=request.result)
                ignored_params_section.update_items(data)
                ignored_params_section.update_items(headers)

            chrome_options = Options()
            # chrome_options.add_argument("--disable-extensions")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--headless=new")
            chrome_options.add_argument("--network_log.preserve-log=true")
            chrome_options.add_argument("--hide-scrollbars")
            chrome_options.set_capability("goog:loggingPrefs", {"performance": "ALL"})
            download_folder = os.path.join(self.working_directory, "downloads")
            os.makedirs(download_folder, exist_ok=True)
            chrome_options.add_experimental_option(
                "prefs",
                {
                    "download.default_directory": download_folder,
                    "download.prompt_for_download": False,
                    "download.directory_upgrade": True,
                    "safebrowsing.enabled": True,
                },
            )

            driver = webdriver.Chrome(options=chrome_options)
            driver.set_window_size(1600, 900)
            driver.set_page_load_timeout(self.request_timeout)
            try:
                driver.get(request.task.fileinfo.uri_info.uri)
            except TimeoutException:
                pass

            time.sleep(5)
            time_slept = 5

            all_perfs = []
            redirects = []
            downloads = {}
            process_perf(driver.get_log("performance"), all_perfs, downloads, redirects)
            while any(download_params["state"] != "completed" for download_params in downloads.values()):
                if time_slept > self.request_timeout:
                    uncompleted_downloads = ResultSection(
                        "Download could not complete in the allocated internal time limit", parent=request.result
                    )
                    for download_params in downloads.values():
                        if download_params["state"] != "completed":
                            uncompleted_downloads.add_line(
                                f'{download_params["receivedBytes"]}/{download_params["totalBytes"]}'
                            )
                    break
                time.sleep(2)
                time_slept += 2
                process_perf(driver.get_log("performance"), all_perfs, downloads, redirects)

            screenshot_path = os.path.join(self.working_directory, "screenshot.png")
            driver.save_screenshot(screenshot_path)
            if os.path.exists(screenshot_path):
                screenshot_section = ResultImageSection(
                    request, title_text="Screenshot of visited page", parent=request.result
                )
                screenshot_section.add_image(
                    path=screenshot_path,
                    name="screenshot.png",
                    description=f"Screenshot of {request.task.fileinfo.uri_info.uri}",
                )
                screenshot_section.promote_as_screenshot()

            if redirects:
                redirect_section = ResultTableSection("Redirections", parent=request.result)
                ResultTableSection("URLs")
                for redirect in redirects:
                    redirect_section.add_row(TableRow(redirect))
                    add_tag(redirect_section, "network.static.uri", redirect["redirecting_url"])
                    redirect_section.add_tag("network.static.ip", redirect["redirecting_ip"])
                    add_tag(redirect_section, "network.static.uri", redirect["redirecting_to"])
                redirect_section.set_column_order(["status", "redirecting_url", "redirecting_ip", "redirecting_to"])

            if downloads:
                download_section = ResultTableSection("Downloaded file(s)", parent=request.result)
                for download_params in downloads.values():
                    download_section.add_row(
                        TableRow(
                            dict(
                                suggestedFilename=download_params["suggestedFilename"],
                                state=download_params["state"],
                                bytes=f'{download_params["receivedBytes"]}/{download_params["totalBytes"]}',
                                url=download_params["url"],
                            )
                        )
                    )
                    # This could break if it does not use the suggestedFilename, or maybe if there is multiple of
                    # the same filename, it would add a ' (1)' at the end?
                    download_path = os.path.join(download_folder, download_params["suggestedFilename"])
                    file_info = self.identify.fileinfo(download_path, skip_fuzzy_hashes=True)
                    if file_info["type"].startswith("archive"):
                        request.add_extracted(download_path, file_info["sha256"], "Archive from the URI")
                    else:
                        request.add_supplementary(download_path, file_info["sha256"], "Downloaded content from the URI")

                download_section.set_column_order(["suggestedFilename", "state", "bytes", "url"])
            with open(os.path.join(self.working_directory, "all_perfs.json"), "w") as f:
                f.write(json.dumps(all_perfs))
            request.add_supplementary(
                os.path.join(self.working_directory, "all_perfs.json"), "all_perfs.json", "Complete performance log"
            )

            driver.quit()
        else:
            # Non-GET request
            r = requests.request(
                verb,
                request.task.fileinfo.uri_info.uri,
                headers=headers,
                data=data.get("data", None),
                json=data.get("json", None),
            )
            requests_content_path = os.path.join(self.working_directory, "requests_content")
            with open(requests_content_path, "wb") as f:
                f.write(r.content)
            file_info = self.identify.fileinfo(requests_content_path, skip_fuzzy_hashes=True)
            if file_info["type"].startswith("archive"):
                request.add_extracted(requests_content_path, file_info["sha256"], "Archive from the URI")
            else:
                request.add_supplementary(requests_content_path, file_info["sha256"], "Full content from the URI")


def process_perf(perf, all_perfs, downloads, redirects):
    for p in perf:
        # print(p)
        m = json.loads(p["message"])["message"]
        all_perfs.append(m)
        # print(m)
        if m["method"] == "Page.downloadWillBegin":
            downloads[m["params"]["guid"]] = m["params"]
        if m["method"] == "Page.downloadProgress":
            downloads[m["params"]["guid"]].update(m["params"])

        if "redirectResponse" in m["params"]:
            if "location" in m["params"]["redirectResponse"]["headers"]:
                redirect_location = m["params"]["redirectResponse"]["headers"]["location"]
            elif "Location" in m["params"]["redirectResponse"]["headers"]:
                redirect_location = m["params"]["redirectResponse"]["headers"]["Location"]
            remote_ip = m["params"]["redirectResponse"]["remoteIPAddress"]
            redirects.append(
                {
                    "status": m["params"]["redirectResponse"]["status"],
                    "redirecting_url": m["params"]["redirectResponse"]["url"],
                    "redirecting_ip": remote_ip,
                    "redirecting_to": redirect_location,
                }
            )

        if (
            m["method"] == "Network.responseReceived"
            and "response" in m["params"]
            and "headers" in m["params"]["response"]
            and "refresh" in m["params"]["response"]["headers"]
        ):
            try:
                refresh = m["params"]["response"]["headers"]["refresh"].split(";", 1)
                if int(refresh[0]) <= 15 and refresh[1].startswith("url="):
                    redirect_location = refresh[1][4:]
                    remote_ip = m["params"]["response"]["remoteIPAddress"]
                    redirects.append(
                        {
                            "status": m["params"]["response"]["status"],
                            "redirecting_url": m["params"]["response"]["url"],
                            "redirecting_ip": remote_ip,
                            "redirecting_to": redirect_location,
                        }
                    )

            except Exception:
                # Maybe log that we weren't able to parse the refresh
                pass
