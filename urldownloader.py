import base64
import hashlib
import json
import os
import re
import subprocess
import tempfile
from urllib.parse import urlparse

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
    ResultTextSection,
    TableRow,
)
from assemblyline_v4_service.common.task import PARENT_RELATION
from PIL import UnidentifiedImageError
from requests.exceptions import ConnectionError

KANGOOROO_FOLDER = os.path.join(os.path.dirname(__file__), "kangooroo")

# Regex from
# https://stackoverflow.com/questions/40939380/how-to-get-file-name-from-content-disposition
# Many tests can be found at http://test.greenbytes.de/tech/tc2231/
UTF8_FILENAME_REGEX = r"filename\*=UTF-8''([\w%\-\.]+)(?:; ?|$)"
ASCII_FILENAME_REGEX = r"filename=([\"']?)(.*?[^\\])\1(?:; ?|$)"


class URLDownloader(ServiceBase):
    def __init__(self, config) -> None:
        super().__init__(config)
        self.identify = Identify(use_cache=False)
        self.request_timeout = self.config.get("request_timeout", 150)
        self.no_sandbox = self.config.get("no_sandbox", False)
        with open(os.path.join(KANGOOROO_FOLDER, "default_conf.yml"), "r") as f:
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

            if self.config["proxies"][request.get_param("proxy")]:
                proxy = self.config["proxies"][request.get_param("proxy")]
                if isinstance(proxy, dict):
                    proxy = proxy[request.task.fileinfo.uri_info.scheme]
                url_proxy = urlparse(proxy)
                if not url_proxy.netloc:
                    # If the proxy was written as
                    # "127.0.0.1:8080"
                    # "user@127.0.0.1:8080"
                    # "user:password@127.0.0.1:8080"
                    url_proxy = urlparse(f"http://{proxy}")
                kangooroo_config["kang-upstream-proxy"]["ip"] = url_proxy.hostname
                kangooroo_config["kang-upstream-proxy"]["port"] = url_proxy.port
                if url_proxy.username:
                    kangooroo_config["kang-upstream-proxy"]["username"] = url_proxy.username
                if url_proxy.password:
                    kangooroo_config["kang-upstream-proxy"]["password"] = url_proxy.password
            else:
                kangooroo_config.pop("kang-upstream-proxy", None)

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
            if self.no_sandbox:
                kangooroo_args.insert(-2, "--no-sandbox")
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
            target_urls = [results["requested_url"]]
            result_section = ResultOrderedKeyValueSection("Results", parent=request.result)
            result_section.add_item("response_code", results["response_code"])
            result_section.add_item("requested_url", results["requested_url"])
            add_tag(result_section, "network.static.uri", results["requested_url"])
            if "requested_url_ip" in results:
                result_section.add_item("requested_url_ip", results["requested_url_ip"])
                result_section.add_tag("network.static.ip", results["requested_url_ip"])
            if "actual_url" in results:
                target_urls.append(results["actual_url"])
                result_section.add_item("actual_url", results["actual_url"])
                add_tag(result_section, "network.static.uri", results["actual_url"])
            if "actual_url_ip" in results:
                result_section.add_item("actual_url_ip", results["actual_url_ip"])
                result_section.add_tag("network.static.ip", results["actual_url_ip"])

            if (
                "requested_url_ip" in results
                and "actual_url_ip" in results
                and results["requested_url_ip"] != results["actual_url_ip"]
            ):
                result_section.add_tag("file.behavior", "IP Redirection change")

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

            # Find any downloaded file
            with open(os.path.join(output_folder, "session.har"), "r") as f:
                har_content = json.load(f)

            downloads = {}
            redirects = []
            response_errors = []
            for entry in har_content["log"]["entries"]:
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
                            "redirecting_ip": entry["serverIPAddress"]
                            if "serverIPAddress" in entry
                            else "Not Available",
                            "redirecting_to": entry["response"]["redirectURL"]
                            if "redirectURL" in entry["response"]
                            else "Not Available",
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
                                    "redirecting_ip": entry["serverIPAddress"]
                                    if "serverIPAddress" in entry
                                    else "Not Available",
                                    "redirecting_to": refresh[1][4:],
                                }
                            )

                    except Exception:
                        # Maybe log that we weren't able to parse the refresh
                        pass

                # Find all content that was downloaded from the servers
                if "size" in entry["response"]["content"] and entry["response"]["content"]["size"] != 0:
                    content_text = entry["response"]["content"].pop("text")
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
                    with tempfile.NamedTemporaryFile(
                        dir=self.working_directory, delete=False, mode="wb"
                    ) as content_file:
                        content_file.write(content)
                    fileinfo = self.identify.fileinfo(content_file.name, skip_fuzzy_hashes=True)
                    content_md5 = fileinfo["md5"]
                    entry["response"]["content"]["_replaced"] = fileinfo["sha256"]

                    if content_md5 not in downloads:
                        downloads[content_md5] = {"path": content_file.name}

                    # The headers could contain the name of the downloaded file
                    if "Content-Disposition" in entry["response"]["headers"]:
                        downloads[content_md5]["filename"] = entry["response"]["headers"]["Content-Disposition"]
                        match = re.search(ASCII_FILENAME_REGEX, downloads[content_md5]["filename"])
                        if match:
                            downloads[content_md5]["filename"] = match.group(2)

                        match = re.search(UTF8_FILENAME_REGEX, downloads[content_md5]["filename"])
                        if match:
                            downloads[content_md5]["filename"] = match.group(1)
                    else:
                        filename = None
                        requested_url = urlparse(entry["request"]["url"])
                        if "." in os.path.basename(requested_url.path):
                            filename = os.path.basename(requested_url.path)

                        if not filename:
                            possible_filename = entry["request"]["url"]
                            if len(possible_filename) > 150:
                                parsed_url = requested_url._replace(fragment="")
                                possible_filename = parsed_url.geturl()

                            if len(possible_filename) > 150:
                                parsed_url = parsed_url._replace(params="")
                                possible_filename = parsed_url.geturl()

                            if len(possible_filename) > 150:
                                parsed_url = parsed_url._replace(query="")
                                possible_filename = parsed_url.geturl()

                            if len(possible_filename) > 150:
                                parsed_url = parsed_url._replace(path="")
                                possible_filename = parsed_url.geturl()
                            filename = possible_filename

                        downloads[content_md5]["filename"] = filename

                    downloads[content_md5]["size"] = entry["response"]["content"]["size"]
                    downloads[content_md5]["url"] = entry["request"]["url"]
                    downloads[content_md5]["mimeType"] = entry["response"]["content"]["mimeType"]
                    downloads[content_md5]["fileinfo"] = fileinfo

                if "_errorMessage" in entry["response"]:
                    response_errors.append((entry["request"]["url"], entry["response"]["_errorMessage"]))

            # Add the modified entries log
            modified_har_filepath = os.path.join(self.working_directory, "modified_session.har")
            with open(modified_har_filepath, "w") as f:
                json.dump(har_content, f)
            request.add_supplementary(modified_har_filepath, "session.har", "Complete session log")

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
                content_section = ResultTableSection("Downloaded Content", parent=request.result)
                for download_params in downloads.values():
                    file_info = download_params["fileinfo"]
                    content_section.add_row(
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
                        download_params["url"] in target_urls
                        or file_info["type"] == "image/svg"
                        or not (
                            file_info["type"].startswith("text/")
                            or file_info["type"].startswith("image/")
                            or file_info["type"] in ["unknown", "code/css"]
                        )
                        or len(downloads) == 1
                    ):
                        request.add_extracted(
                            download_params["path"],
                            download_params["filename"],
                            download_params["url"],
                            parent_relation=PARENT_RELATION.DOWNLOADED,
                        )
                    else:
                        request.add_supplementary(
                            download_params["path"],
                            download_params["filename"],
                            download_params["url"],
                            parent_relation=PARENT_RELATION.DOWNLOADED,
                        )

            if response_errors:
                error_section = ResultTextSection("Responses Error", parent=request.result)
                for response_url, response_error in response_errors:
                    error_section.add_line(f"{response_url}: {response_error}")
        else:
            # Non-GET request
            try:
                r = requests.request(
                    method,
                    request.task.fileinfo.uri_info.uri,
                    headers=data.get("headers", {}),
                    proxies=self.config["proxies"][request.get_param("proxy")],
                    data=data.get("data", None),
                    json=data.get("json", None),
                )
            except ConnectionError:
                error_section = ResultTextSection("Error", parent=request.result)
                error_section.add_line(f"Cannot connect to {request.task.fileinfo.uri_info.hostname}")
                error_section.add_line("This server is currently unavailable")
                return
            requests_content_path = os.path.join(self.working_directory, "requests_content")
            with open(requests_content_path, "wb") as f:
                f.write(r.content)
            file_info = self.identify.fileinfo(requests_content_path, skip_fuzzy_hashes=True)
            if file_info["type"].startswith("archive"):
                request.add_extracted(
                    requests_content_path,
                    file_info["sha256"],
                    "Archive from the URI",
                    parent_relation=PARENT_RELATION.DOWNLOADED,
                )
            else:
                request.add_supplementary(requests_content_path, file_info["sha256"], "Full content from the URI")
