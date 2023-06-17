import json
import os
import re
import subprocess
from tempfile import NamedTemporaryFile
from typing import List, Optional, Tuple
from urllib.parse import urlparse

import requests
from assemblyline.common.identify import Identify
from assemblyline.common.str_utils import safe_str
from assemblyline.odm.base import IP_ONLY_REGEX, IPV4_ONLY_REGEX
from assemblyline_v4_service.common.base import ServiceBase
from assemblyline_v4_service.common.request import ServiceRequest
from assemblyline_v4_service.common.result import (
    Heuristic,
    Result,
    ResultImageSection,
    ResultSection,
    ResultTableSection,
    TableRow,
)

REQUESTS_EXCEPTION_MSG = {
    requests.RequestException: "There was an ambiguous exception that occurred while handling your request.",
    requests.ConnectionError: "A Connection error occurred.",
    requests.HTTPError: "An HTTP error occurred.",
    requests.URLRequired: "A valid URL is required to make a request.",
    requests.TooManyRedirects: "Too many redirects.",
    requests.ConnectTimeout: "The request timed out while trying to connect to the remote server.",
    requests.ReadTimeout: "The server did not send any data in the allotted amount of time.",
    requests.Timeout: "The request timed out.",
}


class URLDownloader(ServiceBase):
    def __init__(self, config) -> None:
        super().__init__(config)
        self.proxy = self.config.get("proxy", {})
        self.headers = self.config.get("headers", {})
        self.timeout = self.config.get("timeout_per_request", 10)
        self.identify = Identify(use_cache=False)

    def fetch_uri(self, uri: str, headers={}) -> Tuple[requests.Response, Optional[str], List[str]]:
        resp = requests.head(uri, allow_redirects=True, timeout=self.timeout, headers=headers, proxies=self.proxy)
        # Only concerned with gathering responses of interest
        if resp.ok or resp.status_code == 403:
            resp = requests.get(uri, allow_redirects=True, headers=headers, timeout=self.timeout, proxies=self.proxy)
            history = [record.headers["Location"] for record in resp.history]
            # Do we have a history to look back on? (redirects)
            if history:
                history.insert(0, uri)
                # If final destination is blocked by a challenge (ie. CloudFlare), mention this in the history
                if "needs to review the security of your connection before proceeding." in resp.text:
                    history.append("<Destination blocked by DDoS Protection>")
            content = resp.content
            if content:
                resp_fh = NamedTemporaryFile(delete=False)
                resp_fh.write(content)
                resp_fh.close()
                return resp, resp_fh.name, history
            return resp, None, history
        return resp, None, []

    def execute(self, request: ServiceRequest) -> None:
        result = Result()
        minimum_maliciousness = int(request.get_param("minimum_maliciousness"))
        urls = []
        submitted_url = request.task.metadata.get("submitted_url")
        if request.get_param("include_submitted_url") and submitted_url and request.task.depth == 0:
            # Make sure this is the first URL fetched
            urls = [(submitted_url, 10000)]

        tags = request.task.tags

        # Only concerned with static/dynamic URIs found by prior services
        urls.extend(tags.get("network.static.uri", []) + tags.get("network.dynamic.uri", []))

        request.temp_submission_data.setdefault("visited_urls", {})

        # Headers that other AL services have sourced for fetching
        al_url_headers = request.temp_submission_data.get("url_headers", {})

        # Check if current file is malicious, if so tag URL that downloaded the file
        task_score = 0
        for tags_tuples in tags.values():
            task_score += sum([tag_tuple[1] for tag_tuple in tags_tuples])

        malicious_urls = []
        for url, hash in request.temp_submission_data["visited_urls"].items():
            if request.sha256 == hash and task_score >= 1000:
                malicious_urls.append(url)

        if malicious_urls:
            ResultSection(
                "Malicious URLs Associated to File",
                body=json.dumps(malicious_urls),
                tags={"network.static.uri": malicious_urls},
                heuristic=Heuristic(1),
                parent=result,
            )

        potential_ip_download = ResultTableSection(title_text="Potential IP-related File Downloads", auto_collapse=True)
        connections_table = ResultTableSection("Established Connections")
        exception_table = ResultTableSection("Attempted Connection Exceptions")
        redirects_table = ResultTableSection("Connection History", heuristic=Heuristic(2))
        screenshot_section = ResultImageSection(request, title_text="Screenshots of visited pages")
        fetch_url = True
        for tag_value, tag_score in sorted(urls, key=lambda x: x[1], reverse=True):
            # Stop fetching if we're past the maliciousness threshold
            if tag_score < minimum_maliciousness:
                fetch_url = False

            if fetch_url:
                # Minimize revisiting the same URIs in the same submission
                if tag_value in request.temp_submission_data["visited_urls"].keys():
                    continue

                headers = self.headers
                if request.get_param("user_agent"):
                    headers["User-Agent"] = request.get_param("user_agent")

                headers.update(al_url_headers.get(tag_value, {}))
                # Write response and attach to submission
                sha256 = None
                try:
                    self.log.debug(f"Trying {tag_value}")
                    resp, fp, history = self.fetch_uri(tag_value, headers=headers)
                    if isinstance(fp, str):
                        file_info = self.identify.fileinfo(fp)
                        file_type = file_info["type"]
                        sha256 = file_info["sha256"]
                        if file_type == "code/html":
                            output_file = f"{tag_value.replace('/', '_')}.png"
                            # If identified to be an HTML document, render it and add to section
                            self.log.info(f"Taking a screenshot of {tag_value}")
                            try:
                                subprocess.run(
                                    [
                                        "google-chrome",
                                        "--headless",
                                        "--hide-scrollbars",
                                        "--no-sandbox",
                                        "--virtual-time-budget=5000",
                                        f"--screenshot={os.path.join(self.working_directory, output_file)}",
                                        tag_value,
                                    ],
                                    timeout=10,
                                    capture_output=True,
                                )
                                screenshot_section.add_image(
                                    path=os.path.join(self.working_directory, output_file),
                                    name=f"{tag_value}.png",
                                    description=f"Screenshot of {tag_value}",
                                )
                            except subprocess.TimeoutExpired:
                                pass

                        self.log.info(f"Success, writing to {fp}...")
                        if sha256 != request.sha256:
                            filename = os.path.basename(urlparse(tag_value).path) or "index.html"
                            request.add_extracted(
                                fp,
                                filename,
                                f"Response from {tag_value}",
                                safelist_interface=self.api_interface,
                                parent_relation="DOWNLOADED",
                                allow_dynamic_recursion=True,
                            )
                        connections_table.add_row(
                            TableRow({"URI": tag_value, "CONTENT PEEK (FIRST 50 BYTES)": safe_str(resp.content[:50])})
                        )
                    elif not resp.ok:
                        self.log.debug(f"Server response exception occurred: {resp.reason}")
                        exception_table.add_row(TableRow({"URI": tag_value, "REASON": resp.reason}))
                    else:
                        # Give general information about the established connections
                        connections_table.add_row(
                            TableRow({"URI": tag_value, "CONTENT PEEK (FIRST 50 BYTES)": "<No data response>"})
                        )

                    if history:
                        redirects_table.add_row(TableRow({"URI": tag_value, "HISTORY": " → ".join(history)}))

                except Exception as e:
                    if e.__class__ in REQUESTS_EXCEPTION_MSG:
                        exception_table.add_row(
                            TableRow({"URI": tag_value, "REASON": REQUESTS_EXCEPTION_MSG[e.__class__]})
                        )
                    else:
                        # Catch any except to ensure fetched files aren't lost due to arbitrary error
                        self.log.warning(f"General except occurred: {e}")
                        exception_table.add_row(TableRow({"URI": tag_value, "REASON": str(e)}))
                finally:
                    request.temp_submission_data["visited_urls"][tag_value] = sha256
            else:
                # Analyse the URL for the possibility of it being a something we should download
                parsed_url = urlparse(tag_value)
                if re.match(IP_ONLY_REGEX, parsed_url.hostname) and "." in os.path.basename(parsed_url.path):
                    # Assumption: If URL host is an IP and the path suggests it's downloading a file, it warrants attention
                    ip_version = "4" if re.match(IPV4_ONLY_REGEX, parsed_url.hostname) else "6"
                    potential_ip_download.add_row(
                        TableRow(
                            {
                                "URL": tag_value,
                                "HOSTNAME": parsed_url.hostname,
                                "IP_VERSION": ip_version,
                                "PATH": parsed_url.path,
                            }
                        )
                    )
                    potential_ip_download.add_tag("network.static.uri", tag_value)
                    potential_ip_download.add_tag("network.static.ip", parsed_url.hostname)
                    if not potential_ip_download.heuristic:
                        potential_ip_download.set_heuristic(3)
                    potential_ip_download.heuristic.add_signature_id(f"ipv{ip_version}")

        if connections_table.body:
            result.add_section(connections_table)
        if redirects_table.body:
            result.add_section(redirects_table)
        if exception_table.body:
            result.add_section(exception_table)
        if potential_ip_download.body:
            result.add_section(potential_ip_download)
        if screenshot_section.body:
            result.add_section(screenshot_section)

        request.result = result
