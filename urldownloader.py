import base64
import hashlib
import json
import os
import subprocess
import tempfile

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
    ResultOrderedKeyValueSection,
    ResultTableSection,
    TableRow,
)
from PIL import UnidentifiedImageError

KANGOOROO_FOLDER = os.path.join(os.path.dirname(__file__), "kangooroo")


class URLDownloader(ServiceBase):
    def __init__(self, config) -> None:
        super().__init__(config)
        self.identify = Identify(use_cache=False)
        self.request_timeout = self.config.get("request_timeout", 150)
        with open(os.path.join(KANGOOROO_FOLDER, "conf.yml"), "r") as f:
            self.default_kangooroo_config = yaml.safe_load(f)

    def execute(self, request: ServiceRequest) -> None:
        result = Result()
        request.result = result

        with open(request.file_path, "r") as f:
            data = yaml.safe_load(f)

        data.pop("uri")
        method = data.pop("method", "GET")
        if method == "GET":
            headers = data.pop("headers", {})
            if data or headers:
                ignored_params_section = ResultKeyValueSection("Ignored params", parent=request.result)
                ignored_params_section.update_items(data)
                ignored_params_section.update_items(headers)

            kangooroo_config = self.default_kangooroo_config.copy()
            kangooroo_config["temporary_folder"] = os.path.join(self.working_directory, "tmp")
            os.makedirs(kangooroo_config["temporary_folder"], exist_ok=True)
            kangooroo_config["output_folder"] = os.path.join(self.working_directory, "output")
            os.makedirs(kangooroo_config["output_folder"], exist_ok=True)

            with tempfile.NamedTemporaryFile(dir=self.working_directory, delete=False, mode="w") as temp_conf:
                yaml.dump(kangooroo_config, temp_conf)

            kangooroo_args = [
                "java",
                "-Dlogback.configurationFile=logback.xml",
                "-jar",
                "KangoorooStandalone.jar",
                "--conf-file",
                temp_conf.name,
                "--dont-use-captcha",  # Don't use captcha for the moment, to be enabled later
                "--url",
                request.task.fileinfo.uri_info.uri,
            ]
            subprocess.run(kangooroo_args, cwd=KANGOOROO_FOLDER, capture_output=True, timeout=self.request_timeout)

            url_md5 = hashlib.md5(request.task.fileinfo.uri_info.uri.encode()).hexdigest()

            output_folder = os.path.join(kangooroo_config["output_folder"], url_md5)

            results_filepath = os.path.join(output_folder, "results.json")
            if not os.path.exists(results_filepath):
                raise Exception(
                    "Kangooroo was probably OOMKilled. Check for memory usage and increase limit as needed."
                )
            with open(results_filepath, "r") as f:
                results = json.load(f)

            # Main result section
            result_section = ResultOrderedKeyValueSection("Results", parent=request.result)
            result_section.add_item("response_code", results["response_code"])
            result_section.add_item("requested_url", results["requested_url"])
            add_tag(result_section, "network.static.uri", results["requested_url"])
            result_section.add_item("requested_url_ip", results["requested_url_ip"])
            result_section.add_tag("network.static.ip", results["requested_url_ip"])
            if "actual_url" in results:
                result_section.add_item("actual_url", results["actual_url"])
                add_tag(result_section, "network.static.uri", results["actual_url"])
            result_section.add_item("actual_url_ip", results["actual_url_ip"])
            result_section.add_tag("network.static.ip", results["actual_url_ip"])

            if results["requested_url_ip"] != results["actual_url_ip"]:
                source_file = os.path.join(output_folder, "source.html")
                if os.path.exists(source_file):
                    request.add_extracted(source_file, "source.html", "Final html page")

            # Screenshot section
            screenshot_path = os.path.join(output_folder, "screenshot.png")
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

            # favicon section
            favicon_path = os.path.join(output_folder, "favicon.ico")
            if os.path.exists(favicon_path):
                try:
                    screenshot_section = ResultImageSection(request, title_text="Favicon of visited page")
                    screenshot_section.add_image(
                        path=favicon_path,
                        name="favicon.ico",
                        description=f"Favicon of {request.task.fileinfo.uri_info.uri}",
                    )
                    request.result.add_section(screenshot_section)
                except UnidentifiedImageError:
                    # Kangooroo is sometime giving html page as favicon...
                    pass

            # Add the har log file
            har_filepath = os.path.join(output_folder, "session.har")
            request.add_supplementary(har_filepath, "session.har", "Complete session log")
            with open(har_filepath, "r") as f:
                entries = json.load(f)["log"]["entries"]

            # Find any downloaded file
            downloads = {}
            redirects = []
            for entry in entries:
                # Convert Kangooroo's list of header to a proper dictionary
                entry["request"]["headers"] = {
                    header["name"]: header["value"] for header in entry["request"]["headers"]
                }
                entry["response"]["headers"] = {
                    header["name"]: header["value"] for header in entry["response"]["headers"]
                }

                # Figure out if there is an http redirect
                if entry["response"]["status"] in [301, 302, 303, 307, 308]:
                    redirects.append(
                        {
                            "status": entry["response"]["status"],
                            "redirecting_url": entry["request"]["url"],
                            "redirecting_ip": entry["serverIPAddress"],
                            "redirecting_to": entry["response"]["redirectURL"],
                        }
                    )

                # Some redirects and hidden in the headers with 200 response codes
                if "refresh" in entry["response"]["headers"]:
                    try:
                        refresh = entry["response"]["headers"]["refresh"].split(";", 1)
                        if int(refresh[0]) <= 15 and refresh[1].startswith("url="):
                            redirects.append(
                                {
                                    "status": entry["response"]["status"],
                                    "redirecting_url": entry["request"]["url"],
                                    "redirecting_ip": entry["serverIPAddress"],
                                    "redirecting_to": refresh[1][4:],
                                }
                            )

                    except Exception:
                        # Maybe log that we weren't able to parse the refresh
                        pass

                # Find all content that was downloaded from the servers
                if "size" in entry["response"]["content"] and entry["response"]["content"]["size"] != 0:
                    content_text = entry["response"]["content"]["text"]
                    if (
                        "encoding" in entry["response"]["content"]
                        and entry["response"]["content"]["encoding"] == "base64"
                    ):
                        try:
                            content = base64.b64decode(content_text)
                        except Exception:
                            content = content_text.encode()
                    else:
                        content = content_text.encode()
                    content_md5 = hashlib.md5(content).hexdigest()
                    content_path = os.path.join(self.working_directory, content_md5)
                    with open(content_path, "wb") as f:
                        f.write(content)

                    if content_md5 not in downloads:
                        downloads[content_md5] = {"path": content_path, "type": "content"}

                    downloads[content_md5]["filename"] = entry["request"]["url"]

                    # The headers could contain the name of the downloaded file
                    if "Content-Disposition" in entry["response"]["headers"]:
                        downloads[content_md5]["filename"] = entry["response"]["headers"]["Content-Disposition"]
                        if downloads[content_md5]["filename"].startswith("attachment; filename="):
                            downloads[content_md5]["filename"] = downloads[content_md5]["filename"][21:]
                            # Flag that file as a proper download instead of an anciliary file
                            downloads[content_md5]["type"] = "download"

                    downloads[content_md5]["size"] = entry["response"]["content"]["size"]
                    downloads[content_md5]["url"] = entry["request"]["url"]
                    downloads[content_md5]["mimeType"] = entry["response"]["content"]["mimeType"]
                    downloads[content_md5]["fileinfo"] = self.identify.fileinfo(content_path, skip_fuzzy_hashes=True)

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
                download_section = ResultTableSection("Downloaded file(s)")
                content_section = ResultTableSection("Content file(s)")
                for download_params in downloads.values():
                    file_info = download_params["fileinfo"]
                    (download_section if download_params["type"] == "download" else content_section).add_row(
                        TableRow(
                            dict(
                                Filename=download_params["filename"],
                                Size=download_params["size"],
                                mimeType=download_params["mimeType"],
                                url=download_params["url"],
                                SHA256=file_info["sha256"],
                            )
                        )
                    )
                    if (
                        download_params["type"] == "download"
                        or file_info["type"].startswith("archive")
                        or len(downloads) == 1
                    ):
                        request.add_extracted(
                            download_params["path"], download_params["filename"], download_params["url"]
                        )
                    else:
                        request.add_supplementary(
                            download_params["path"], download_params["filename"], download_params["url"]
                        )
                if download_section.body:
                    request.result.add_section(download_section)
                if content_section.body:
                    request.result.add_section(content_section)
        else:
            # Non-GET request
            r = requests.request(
                method,
                request.task.fileinfo.uri_info.uri,
                headers=data.get("headers", {}),
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
