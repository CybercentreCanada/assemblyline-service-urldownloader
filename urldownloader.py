import base64
import hashlib
import json
import math
import os
import re
import subprocess
import tempfile
import xml.etree.ElementTree as ET
from datetime import datetime
from urllib.parse import urlparse

import requests
import yaml
from assemblyline.common.identify import Identify
from assemblyline.odm.base import DATEFORMAT
from assemblyline.odm.models.ontology.results.http import HTTP as HTTPResult
from assemblyline.odm.models.ontology.results.network import NetworkConnection
from assemblyline.odm.models.ontology.results.sandbox import Sandbox
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
from bs4 import BeautifulSoup
from PIL import UnidentifiedImageError
from requests.exceptions import ConnectionError, TooManyRedirects

KANGOOROO_FOLDER = os.path.join(os.path.dirname(__file__), "kangooroo")

# Regex from
# https://stackoverflow.com/questions/40939380/how-to-get-file-name-from-content-disposition
# Many tests can be found at http://test.greenbytes.de/tech/tc2231/
UTF8_FILENAME_REGEX = r"filename\*=UTF-8''([\w%\-\.]+)(?:; ?|$)"
ASCII_FILENAME_REGEX = r"filename=([\"']?)(.*?[^\\])\1(?:; ?|$)"


def detect_open_directory(request: ServiceRequest, soup: BeautifulSoup):
    if not soup.title or "index of" not in soup.title.string.lower():
        return

    open_directory_links = []
    open_directory_folders = []
    for a in soup.find_all("a", href=True):
        if "://" in a["href"][:10] and a["href"][0] != ".":
            continue
        if a["href"] == "..":
            # Link to the parent directory
            continue
        if a["href"][0] == "?":
            # Probably just some table ordering
            continue
        if a["href"][0] == "/":
            # Check if it is the root or a parent directory
            if a["href"] == "/" or request.task.fileinfo.uri_info.path.startswith(a["href"]):
                continue

        if a["href"].endswith("/"):
            open_directory_folders.append(a["href"])
        else:
            open_directory_links.append(a["href"])

    if open_directory_links or open_directory_folders:
        open_directory_section = ResultTextSection("Open Directory Detected", parent=request.result)
        if open_directory_links:
            open_directory_section.add_line(f"File{'s' if len(open_directory_links) > 1 else ''}:")

        for link in open_directory_links:
            # Append the full website, remove the '.' from the link
            while link[:2] == "./":
                link = link[2:]
            link = f"{request.task.fileinfo.uri_info.uri.rstrip('/')}/{link}"
            open_directory_section.add_line(link)
            add_tag(open_directory_section, "network.static.uri", link)

        if open_directory_folders:
            open_directory_section.add_line(f"Folder{'s' if len(open_directory_folders) > 1 else ''}:")

        for link in open_directory_folders:
            # Append the full website, remove the '.' from the link
            while link[:2] == "./":
                link = link[2:]
            link = f"{request.task.fileinfo.uri_info.uri.rstrip('/')}/{link}"
            open_directory_section.add_line(link)
            add_tag(open_directory_section, "network.static.uri", link)


def detect_webdav_listing(request: ServiceRequest, content: bytes):
    root = ET.fromstring(content)
    namespace = {"d": "DAV:"}
    links = []
    for response in root.findall("d:response", namespace):
        href = response.find("d:href", namespace)
        if href is not None:
            links.append(href.text)

    if not links:
        return

    webdav_section = ResultTextSection("WebDav Listing Detected", parent=request.result)
    root_url = urlparse(request.task.fileinfo.uri_info.uri)
    root_url = root_url._replace(fragment="")._replace(params="")._replace(query="")._replace(path="").geturl()
    for link in links:
        # Append the root website
        link = f"{root_url}{link}"
        webdav_section.add_line(link)
        add_tag(webdav_section, "network.static.uri", link)


class URLDownloader(ServiceBase):
    def __init__(self, config=None) -> None:
        super().__init__(config)
        self.identify = Identify(use_cache=False)
        self.request_timeout = self.config.get("request_timeout", 150)
        self.do_not_download_regexes = [re.compile(x) for x in self.config.get("do_not_download_regexes", [])]
        self.no_sandbox = self.config.get("no_sandbox", False)
        with open(os.path.join(KANGOOROO_FOLDER, "default_conf.yml"), "r") as f:
            self.default_kangooroo_config = yaml.safe_load(f)

    def execute_kangooroo(self, request: ServiceRequest):

        # Setup configurations for running Kangooroo
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

        # create the file that we use to run Kangooroo
        with tempfile.NamedTemporaryFile(dir=self.working_directory, delete=False, mode="w") as temp_conf:
            yaml.dump(kangooroo_config, temp_conf)


        # Set up environment variable and commandline arguments for running kangooroo
        env_variables = {
            "JAVA_OPTS": f"-Xmx{math.floor(self.service_attributes.docker_config.ram_mb*0.75)}m"
        }
        kangooroo_args = [
                "./bin/kangooroo",
                "--conf-file",
                temp_conf.name,
                "-mods",
                "summary,captcha",
                "--simple-result",
                "--url",
                request.task.fileinfo.uri_info.uri,
        ]
        if self.no_sandbox:
            kangooroo_args.insert(-2, "--no-sandbox")
        try:
            subprocess.run(kangooroo_args, cwd=KANGOOROO_FOLDER, capture_output=True, timeout=self.request_timeout, env=env_variables)
        except subprocess.TimeoutExpired:
            timeout_section = ResultTextSection("Request timed out", parent=request.result)
            timeout_section.add_line(
                f"Timeout of {self.request_timeout} seconds was not enough to process the query fully."
            )
            return None, None

        url_md5 = hashlib.md5(request.task.fileinfo.uri_info.uri.encode()).hexdigest()

        output_folder = os.path.join(kangooroo_config["output_folder"], url_md5)
        if not os.path.exists(output_folder):
            possible_folders = os.listdir(kangooroo_config["output_folder"])
            if len(possible_folders) == 0:
                raise Exception(
                    (
                        "No Kangooroo output folder found. Kangooroo may have been OOMKilled. "
                        "Check for memory usage and increase limit as needed."
                    )
                )
            elif len(possible_folders) != 1:
                raise Exception(
                    (
                        "Multiple Kangooroo output folders found. Unknown situation happened, you can try "
                        "submitting this URL again to see if it would help."
                    )
                )
            else:
                url_hash_mismatch = ResultTextSection("URL hash mismatch", parent=request.result)
                url_hash_mismatch.add_line(
                    (
                        f"URL '{request.task.fileinfo.uri_info.uri}' ({url_md5}) was requested "
                        f"but a different URL was fetched ({possible_folders[0]})."
                    )
                )
                output_folder = os.path.join(kangooroo_config["output_folder"], possible_folders[0])

        results_filepath = os.path.join(output_folder, "results.json")
        if not os.path.exists(results_filepath):
            raise Exception(
                (
                    "No Kangooroo results.json found. Kangooroo may have been OOMKilled. "
                    "Check for memory usage and increase limit as needed."
                )
            )

        return output_folder, results_filepath



    def send_http_request(self, method, request: ServiceRequest, data: dict):
        try:

            r = requests.request(
                method,
                request.task.fileinfo.uri_info.uri,
                headers=data.get("headers", {}),
                proxies=self.config["proxies"][request.get_param("proxy")],
                data=data.get("data", None),
                json=data.get("json", None),
                cookies = data.get("cookies", None),
                stream = True
            )
        except ConnectionError:
            error_section = ResultTextSection("Error", parent=request.result)
            error_section.add_line(f"Cannot connect to {request.task.fileinfo.uri_info.hostname}")
            error_section.add_line("This server is currently unavailable")
            return
        except TooManyRedirects as e:
            error_section = ResultTextSection("Too many redirects", parent=request.result)
            error_section.add_line(f"Cannot connect to {request.task.fileinfo.uri_info.hostname}")

            redirect_section = ResultTableSection("Redirections", parent=error_section)
            for redirect in e.response.history:
                redirect_section.add_row(
                    TableRow({"status": redirect.status_code, "redirecting_url": redirect.url})
                )
                add_tag(redirect_section, "network.static.uri", redirect.url)
            redirect_section.set_column_order(["status", "redirecting_url"])
            return None

        requests_content_path = os.path.join(self.working_directory, "requests_content")
        with open(requests_content_path, "wb") as f:
            for chunk in r.iter_content():
                f.write(chunk)

        return requests_content_path


    def execute(self, request: ServiceRequest) -> None:
        result = Result()
        request.result = result

        with open(request.file_path, "r") as f:
            data = yaml.safe_load(f)

        data.pop("uri")
        for no_dl in self.do_not_download_regexes:
            # Do nothing if we are not supposed to scan that URL
            if no_dl.match(request.task.fileinfo.uri_info.uri):
                return

        method = data.pop("method", "GET")
        if method == "GET":
            if "\x00" in request.task.fileinfo.uri_info.uri:
                # We won't try to fetch URIs with a null byte using subprocess.
                # This would cause a fork_exec issue. We will return an empty result instead.
                return
            headers = data.pop("headers", {})
            if data or headers:
                ignored_params_section = ResultKeyValueSection("Ignored params", parent=request.result)
                ignored_params_section.update_items(data)
                ignored_params_section.update_items(headers)

            # use Kangooroo to fetch URL
            output_folder, results_filepath = self.execute_kangooroo(request)

            if (results_filepath):
                request.add_supplementary(results_filepath, "results.json", "Kangooroo Result Output.")
            else:
                return None


            with open(results_filepath, "r") as f:
                results = json.load(f)

            if results is None:
                raise Exception(
                    (
                        "No Kangooroo results found. "
                    )
                )

            result_summary = results.get("summary", {})
            result_experiment = results.get("experiment", {})
            result_params = result_experiment.get("params", {})
            result_execution = result_experiment.get("execution", {})

            sandbox_details = {
                "analysis_metadata": {
                    "start_time": datetime.strptime(result_execution["startTime"], "%a %b %d %H:%M:%S UTC %Y").strftime(
                        DATEFORMAT
                    )
                },
                "sandbox_name": result_experiment["engineInfo"]["engineName"],
                "sandbox_version": result_experiment["engineInfo"]["engineVersion"],
            }
            http_result = {
                "response_code": result_summary["fetchResult"]["response_code"],
            }

            # check if kangooroo has unfinished download file. If so, we do a GET request to fetch that file again.
            download_status = result_execution.get("downloadStatus", None)

            if download_status == "INCOMPLETE_DOWNLOAD":

                data["headers"] = {** result_summary.get("requestHeaders", {}), **data.get("headers", {})}
                data["cookies"] = result_summary.get("sessionCookies", {})


                requests_content_path = self.send_http_request("GET", request, data)

                file_info = self.identify.fileinfo(requests_content_path, skip_fuzzy_hashes=True, calculate_entropy=False)
                if file_info["type"].startswith("archive"):
                    request.add_extracted(
                        requests_content_path,
                        file_info["sha256"],
                        "Archive from the URI",
                        parent_relation=PARENT_RELATION.DOWNLOADED,
                    )
                else:
                    request.add_supplementary(requests_content_path, file_info["sha256"], "Full content from the URI")


            # Main result section

            requested_url = result_summary.get("requestedUrl", {})
            actual_url = result_summary.get("actualUrl", {})

            target_urls = [requested_url["url"]]
            result_section = ResultOrderedKeyValueSection("Results", parent=request.result)
            result_section.add_item("response_code", result_summary["fetchResult"]["response_code"])
            result_section.add_item("requested_url", requested_url["url"])
            add_tag(result_section, "network.static.uri", requested_url["url"])
            if "ip" in requested_url:
                result_section.add_item("requested_url_ip", requested_url["ip"])
                result_section.add_tag("network.static.ip", requested_url["ip"])
            if actual_url:
                target_urls.append(actual_url["url"])
                result_section.add_item("actual_url", actual_url["url"])
                add_tag(result_section, "network.static.uri", actual_url["url"])
            if "ip" in actual_url:
                result_section.add_item("actual_url_ip", actual_url["ip"])
                result_section.add_tag("network.static.ip", actual_url["ip"])

            if (
                ("ip" in  actual_url
                and "ip" in requested_url)
                and actual_url["ip"] != requested_url["ip"]
            ):
                result_section.add_tag("file.behavior", "IP Redirection change")

            if (
                ("url" in requested_url
                and "url" in actual_url )
                and requested_url["url"] != actual_url["url"]
            ):
                http_result["redirection_url"] = actual_url["url"]

            if result_params.get("windowSize", False):
                sandbox_details["analysis_metadata"]["window_size"] = result_params["windowSize"]

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
                    fileinfo = self.identify.fileinfo(favicon_path, skip_fuzzy_hashes=True, calculate_entropy=False)
                    http_result["favicon"] = {
                        "md5": fileinfo["md5"],
                        "sha1": fileinfo["sha1"],
                        "sha256": fileinfo["sha256"],
                        "size": fileinfo["size"],
                    }
                except UnidentifiedImageError:
                    # Kangooroo is sometime giving html page as favicon...
                    pass

            source_path = os.path.join(output_folder, "source.html")
            if os.path.exists(source_path):
                with open(source_path, "rb") as f:
                    data = f.read()

                soup = BeautifulSoup(data, features="lxml")
                if soup.title and soup.title.string:
                    http_result["title"] = soup.title.string

            # Find any downloaded file
            with open(os.path.join(output_folder, "session.har"), "r") as f:
                har_content = json.load(f)

            downloads = {}
            redirects = []
            response_errors = []
            for entry in har_content["log"]["entries"]:
                # Convert Kangooroo's list of header to a proper dictionary
                request_headers = {header["name"]: header["value"] for header in entry["request"]["headers"]}
                response_headers = {header["name"]: header["value"] for header in entry["response"]["headers"]}

                http_details = {
                    "request_uri": entry["request"]["url"],
                    "request_headers": request_headers,
                    "request_method": entry["request"]["method"],
                    "response_headers": response_headers,
                    "response_status_code": entry["response"]["status"],
                }

                # Figure out if there is an http redirect
                if entry["response"]["status"] in [301, 302, 303, 307, 308]:
                    redirects.append(
                        {
                            "status": entry["response"]["status"],
                            "redirecting_url": entry["request"]["url"],
                            "redirecting_ip": (
                                entry["serverIPAddress"] if "serverIPAddress" in entry else "Not Available"
                            ),
                            "redirecting_to": (
                                entry["response"]["redirectURL"]
                                if "redirectURL" in entry["response"]
                                else "Not Available"
                            ),
                        }
                    )

                # Some redirects and hidden in the headers with 200 response codes
                if "refresh" in response_headers:
                    try:
                        refresh = response_headers["refresh"].split(";", 1)
                        if int(refresh[0]) <= 15 and refresh[1].startswith("url="):
                            redirects.append(
                                {
                                    "status": entry["response"]["status"],
                                    "redirecting_url": entry["request"]["url"],
                                    "redirecting_ip": (
                                        entry["serverIPAddress"] if "serverIPAddress" in entry else "Not Available"
                                    ),
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

                    fileinfo = self.identify.fileinfo(
                        content_file.name, skip_fuzzy_hashes=True, calculate_entropy=False
                    )
                    content_md5 = fileinfo["md5"]
                    entry["response"]["content"]["_replaced"] = fileinfo["sha256"]
                    http_details["response_content_fileinfo"] = {
                        "md5": fileinfo["md5"],
                        "sha1": fileinfo["sha1"],
                        "sha256": fileinfo["sha256"],
                        "size": fileinfo["size"],
                    }
                    if "mimeType" in entry["response"]["content"] and entry["response"]["content"]["mimeType"]:
                        http_details["response_content_mimetype"] = entry["response"]["content"]["mimeType"]

                    if content_md5 not in downloads:
                        downloads[content_md5] = {"path": content_file.name}

                    # The headers could contain the name of the downloaded file
                    if (
                        "Content-Disposition" in response_headers
                        # Some servers are returning an empty "Content-Disposition"
                        and response_headers["Content-Disposition"]
                    ):
                        downloads[content_md5]["filename"] = response_headers["Content-Disposition"]
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

                    if not downloads[content_md5]["filename"]:
                        downloads[content_md5]["filename"] = f"UnknownFilename_{fileinfo['sha256'][:8]}"
                    downloads[content_md5]["size"] = entry["response"]["content"]["size"]
                    downloads[content_md5]["url"] = entry["request"]["url"]
                    downloads[content_md5]["mimeType"] = entry["response"]["content"]["mimeType"]
                    downloads[content_md5]["fileinfo"] = fileinfo

                    if entry["response"]["status"] == 207 and downloads[content_md5]["mimeType"].startswith("text/xml"):
                        detect_webdav_listing(request, content)

                    if downloads[content_md5]["url"] in target_urls:
                        try:
                            soup = BeautifulSoup(content, features="lxml")
                            detect_open_directory(request, soup)
                        except Exception:
                            pass

                if "_errorMessage" in entry["response"]:
                    response_errors.append((entry["request"]["url"], entry["response"]["_errorMessage"]))

                self.ontology.add_result_part(
                    model=NetworkConnection, data={"http_details": http_details, "connection_type": "http"}
                )

            # Add the modified entries log
            modified_har_filepath = os.path.join(self.working_directory, "modified_session.har")
            with open(modified_har_filepath, "w") as f:
                json.dump(har_content, f)

            request.add_supplementary(modified_har_filepath, "session.har", "Complete session log")


            if redirects:
                http_result["redirects"] = []
                redirect_section = ResultTableSection("Redirections", parent=request.result)
                for redirect in redirects:
                    redirect_section.add_row(TableRow(redirect))
                    add_tag(redirect_section, "network.static.uri", redirect["redirecting_url"])
                    redirect_section.add_tag("network.static.ip", redirect["redirecting_ip"])
                    add_tag(redirect_section, "network.static.uri", redirect["redirecting_to"])
                    http_result["redirects"].append(
                        {"from_url": redirect["redirecting_url"], "to_url": redirect["redirecting_to"]}
                    )
                redirect_section.set_column_order(["status", "redirecting_url", "redirecting_ip", "redirecting_to"])

            self.ontology.add_result_part(model=Sandbox, data=sandbox_details)
            self.ontology.add_result_part(model=HTTPResult, data=http_result)

            if downloads:
                content_section = ResultTableSection("Downloaded Content")
                safelisted_section = ResultTableSection("Safelisted Content")
                for download_params in downloads.values():
                    file_info = download_params["fileinfo"]
                    added = True

                    if (
                        download_params["url"] in target_urls
                        or len(downloads) == 1
                        or re.match(request.get_param("regex_extract_filetype"), file_info["type"])
                        or (
                            request.get_param("extract_unmatched_filetype")
                            and not re.match(request.get_param("regex_supplementary_filetype"), file_info["type"])
                        )
                    ):
                        added = request.add_extracted(
                            download_params["path"],
                            download_params["filename"],
                            download_params["url"] or "Unknown URL",
                            safelist_interface=self.api_interface,
                            parent_relation=PARENT_RELATION.DOWNLOADED,
                        )
                    else:
                        request.add_supplementary(
                            download_params["path"],
                            download_params["filename"],
                            download_params["url"] or "Unknown URL",
                            parent_relation=PARENT_RELATION.DOWNLOADED,
                        )

                    (content_section if added else safelisted_section).add_row(
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

                if content_section.body:
                    request.result.add_section(content_section)
                if safelisted_section.body:
                    request.result.add_section(safelisted_section)

            if response_errors:
                error_section = ResultTextSection("Responses Error", parent=request.result)
                for response_url, response_error in response_errors:
                    error_section.add_line(f"{response_url}: {response_error}")
        else:
            # Non-GET request
            requests_content_path = self.send_http_request(self, method, request, data)

            if not requests_content_path:
                return

            file_info = self.identify.fileinfo(requests_content_path, skip_fuzzy_hashes=True, calculate_entropy=False)
            if file_info["type"].startswith("archive"):
                request.add_extracted(
                    requests_content_path,
                    file_info["sha256"],
                    "Archive from the URI",
                    parent_relation=PARENT_RELATION.DOWNLOADED,
                )
            else:
                request.add_supplementary(requests_content_path, file_info["sha256"], "Full content from the URI")
