import hashlib
import json
import os
import subprocess

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

            kangooroo_args = ["java", "-jar", "KangoorooStandalone.jar", "-u", request.task.fileinfo.uri_info.uri]
            subprocess.run(kangooroo_args, capture_output=True)

            url_md5 = hashlib.md5(request.task.fileinfo.uri_info.uri.encode()).hexdigest()

            drop_folder = f"result/{url_md5}/drops"
            drops_content = os.listdir(drop_folder)
            workspace_name = [folder for folder in drops_content if folder.startswith("workspace_")][0]
            drops_workspace = os.path.join(drop_folder, workspace_name)

            results_filepath = os.path.join(drops_workspace, "results.json")
            with open(results_filepath, "r") as f:
                results = json.load(f)

            # Main result section
            result_section = ResultOrderedKeyValueSection("Results", parent=request.result)
            result_section.add_item("response_code", results["response_code"])
            result_section.add_item("requested_url", results["requested_url"]["url"])
            result_section.add_item("requested_url_ip", results["requested_url_ip"])
            result_section.add_item("actual_url", results["actual_url"])
            result_section.add_item("actual_url_ip", results["actual_url_ip"])
            add_tag(result_section, "network.static.uri", results["requested_url"]["url"])
            result_section.add_tag("network.static.ip", results["requested_url_ip"])
            add_tag(result_section, "network.static.uri", results["actual_url"])
            result_section.add_tag("network.static.ip", results["actual_url_ip"])
            if results["requested_url_ip"] != results["actual_url_ip"]:
                source_file = os.path.join(drops_workspace, "source.html")
                if os.path.exists(source_file):
                    request.add_extracted(source_file, "source.html", "Final html page")

            # Screenshot section
            screenshot_path = os.path.join(drops_workspace, "screenshot.png")
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
            favicon_path = os.path.join(drops_workspace, "favicon.ico")
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
            har_filepath = os.path.join(drops_workspace, "session.har")
            request.add_supplementary(har_filepath, "session.har", "Complete session log")
            with open(har_filepath, "r") as f:
                entries = json.load(f)["log"]["entries"]

            # Find any downloaded file
            downloads = {}
            for name in drops_content:
                if not name.startswith("download"):
                    continue
                with open(os.path.join(drop_folder, name), "rb") as f:
                    file_md5 = hashlib.md5(f.read()).hexdigest()
                downloads[file_md5] = {"path": os.path.join(drop_folder, name), "type": "download"}

            redirects = []
            for entry in entries:
                # print(entry)

                # Convert Kangooroo's list of header to a proper dictionary
                entry["request"]["headers"] = {
                    header["name"]: header["value"] for header in entry["request"]["headers"]
                }
                entry["response"]["headers"] = {
                    header["name"]: header["value"] for header in entry["response"]["headers"]
                }

                if entry["response"]["status"] in [301, 302, 303, 307, 308]:
                    redirects.append(
                        {
                            "status": entry["response"]["status"],
                            "redirecting_url": entry["request"]["url"],
                            "redirecting_ip": entry["serverIPAddress"],
                            "redirecting_to": entry["response"]["redirectURL"],
                        }
                    )

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

                if "size" in entry["response"]["content"] and entry["response"]["content"]["size"] != 0:
                    if "comment" in entry["response"]["content"] and entry["response"]["content"]["comment"].startswith(
                        "removed;md5:"
                    ):
                        file_md5 = entry["response"]["content"]["comment"][12:]
                        if file_md5 in downloads and "Content-Disposition" in entry["response"]["headers"]:
                            downloads[file_md5]["filename"] = entry["response"]["headers"]["Content-Disposition"]
                            if downloads[file_md5]["filename"].startswith("attachment; filename="):
                                downloads[file_md5]["filename"] = downloads[file_md5]["filename"][21:]
                            downloads[file_md5]["size"] = entry["response"]["content"]["size"]
                            downloads[file_md5]["url"] = entry["request"]["url"]
                            downloads[file_md5]["mimeType"] = entry["response"]["content"]["mimeType"]
                        else:
                            # What happened with the content?
                            pass
                    else:
                        content = entry["response"]["content"]["text"].encode()
                        content_md5 = hashlib.md5(content).hexdigest()
                        content_path = os.path.join(self.working_directory, content_md5)
                        with open(content_path, "wb") as f:
                            f.write(content)

                        if content_md5 not in downloads:
                            downloads[content_md5] = {"path": content_path, "type": "content"}

                        downloads[content_md5]["filename"] = entry["request"]["url"]
                        downloads[content_md5]["size"] = entry["response"]["content"]["size"]
                        downloads[content_md5]["url"] = entry["request"]["url"]
                        downloads[content_md5]["mimeType"] = entry["response"]["content"]["mimeType"]

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
                    (download_section if download_params["type"] == "download" else content_section).add_row(
                        TableRow(
                            dict(
                                Filename=download_params["filename"],
                                Size=download_params["size"],
                                mimeType=download_params["mimeType"],
                                url=download_params["url"],
                            )
                        )
                    )
                    file_info = self.identify.fileinfo(download_params["path"], skip_fuzzy_hashes=True)
                    if file_info["type"].startswith("archive"):
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
