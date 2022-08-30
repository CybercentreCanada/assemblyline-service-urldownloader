import requests
import hashlib
import json

from assemblyline_v4_service.common.base import ServiceBase
from assemblyline_v4_service.common.request import ServiceRequest
from assemblyline_v4_service.common.result import Result, ResultSection, ResultTableSection, TableRow, Heuristic

from tempfile import NamedTemporaryFile
from typing import Union

REQUESTS_EXCEPTION_MSG = {
    requests.RequestException: "There was an ambiguous exception that occurred while handling your request.",
    requests.ConnectionError: "A Connection error occurred.",
    requests.HTTPError: "An HTTP error occurred.",
    requests.URLRequired: "A valid URL is required to make a request.",
    requests.TooManyRedirects: "Too many redirects.",
    requests.ConnectTimeout: "The request timed out while trying to connect to the remote server.",
    requests.ReadTimeout: "The server did not send any data in the allotted amount of time.",
    requests.Timeout: "The request timed out."
}


class URLDownloader(ServiceBase):
    def __init__(self, config) -> None:
        super().__init__(config)
        self.proxy = self.config.get('proxy', {})
        self.headers = self.config.get('headers', {})
        self.timeout = self.config.get('timeout_per_request', 10)

    def fetch_uri(self, uri: str, headers={}) -> Union[str, requests.Response]:
        resp = requests.head(uri, allow_redirects=True, timeout=self.timeout, headers=headers, proxies=self.proxy)
        # Only concerned with gathering responses of interest
        if resp.ok:
            resp_fh = NamedTemporaryFile(delete=False)
            content = requests.get(uri, allow_redirects=True, headers=headers, timeout=self.timeout).content
            sha256 = hashlib.sha256(content).hexdigest()
            resp_fh.write(content)
            resp_fh.close()
            return resp_fh.name, sha256
        return resp, None

    def execute(self, request: ServiceRequest) -> None:
        result = Result()
        submitted_url = []
        minimum_maliciousness = request.get_param('minimum_maliciousness')
        headers = self.headers
        if request.get_param('user_agent'):
            headers['User-Agent'] = request.get_param('user_agent')

        # Code to be used when responsibility of fetching submitted_url is moved to service from UI
        # -----------------------------------------------------------------------------------------
        submitted_url = request.task.metadata.get('submitted_url')
        # Make sure this is the first URL fetched
        urls = [(submitted_url, 10000)] if submitted_url and request.task.depth == 0 else []

        # Distinguish between only fetching the submitted_url vs all in the submission
        if not request.get_param('submitted_url_only'):
            # Only concerned with static/dynamic URIs found by prior services
            tags = request.task.tags
            urls.extend(tags.get('network.static.uri', []) + tags.get('network.dynamic.uri', []))

        request.temp_submission_data.setdefault('visited_urls', {})

        # Check if current file is malicious, if so tag URL that downloaded the file
        malicious_urls = []
        for url, hash in request.temp_submission_data['visited_urls'].items():
            if request.sha256 == hash:
                malicious_urls.append(url)

        if malicious_urls:
            ResultSection("Malicious URLs Associated to File", body=json.dumps(malicious_urls),
                          tags={'network.static.uri': malicious_urls}, heuristic=Heuristic(1), parent=result)

        exception_table = ResultTableSection("Attempted Connection Exceptions")
        for tag_value, tag_score in sorted(urls, key=lambda x: x[1], reverse=True):
            # Minimize revisiting the same URIs in the same submission
            if tag_score < minimum_maliciousness:
                break

            if tag_value in request.temp_submission_data['visited_urls'].keys():
                continue

            # Write response and attach to submission
            sha256 = None
            try:
                self.log.debug(f'Trying {tag_value}')
                fp, sha256 = self.fetch_uri(tag_value, headers=headers)
                if isinstance(fp, str):
                    self.log.info(f'Success, writing to {fp}...')
                    request.add_extracted(fp, tag_value, f"Response from {tag_value}",
                                          safelist_interface=self.api_interface)
                else:
                    self.log.debug(f'Server response except occurred: {fp.reason}')
                    exception_table.add_row(TableRow({'URI': tag_value, 'REASON': fp.reason}))
            except Exception as e:
                if e.__class__ in REQUESTS_EXCEPTION_MSG:
                    exception_table.add_row(TableRow({'URI': tag_value, 'REASON': REQUESTS_EXCEPTION_MSG[e.__class__]}))
                else:
                    # Catch any except to ensure fetched files aren't lost due to arbitrary error
                    self.log.warning(f'General except occurred: {e}')
                    exception_table.add_row(TableRow({'URI': tag_value, 'REASON': str(e)}))
            finally:
                request.temp_submission_data['visited_urls'][tag_value] = sha256

        if exception_table.body:
            result.add_section(exception_table)

        request.result = result
