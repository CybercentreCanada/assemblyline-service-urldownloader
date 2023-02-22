import os
import requests
import hashlib
import json

from assemblyline.common.identify import Identify
from assemblyline_v4_service.common.base import ServiceBase
from assemblyline_v4_service.common.request import ServiceRequest
from assemblyline_v4_service.common.result import Result, ResultSection, ResultImageSection, ResultTableSection, TableRow, Heuristic

from html2image import Html2Image
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
        self.identify = Identify(use_cache=False)

    def fetch_uri(self, uri: str, headers={}) -> Union[str, requests.Response]:
        resp = requests.head(uri, allow_redirects=True, timeout=self.timeout, headers=headers, proxies=self.proxy)
        # Only concerned with gathering responses of interest
        if resp.ok or resp.status_code == 403:
            resp_fh = NamedTemporaryFile(delete=False)
            resp = requests.get(uri, allow_redirects=True, headers=headers, timeout=self.timeout)
            history = [record.headers['Location'] for record in resp.history]
            # Do we have a history to look back on? (redirects)
            if history:
                history.insert(0, uri)
                # If final destination is blocked by a challenge (ie. CloudFlare), mention this in the history
                if "needs to review the security of your connection before proceeding." in resp.text:
                    history.append('<Destination blocked by DDoS Protection>')
            content = resp.content
            sha256 = hashlib.sha256(content).hexdigest()
            resp_fh.write(content)
            resp_fh.close()
            return resp_fh.name, sha256, history
        return resp, None, []

    def execute(self, request: ServiceRequest) -> None:
        result = Result()
        submitted_url = []

        minimum_maliciousness = int(request.get_param('minimum_maliciousness'))
        urls = []
        submitted_url = request.task.metadata.get('submitted_url')
        if request.get_param('analyze_submitted_url') and submitted_url and request.task.depth == 0:
            # Make sure this is the first URL fetched
            urls = [(submitted_url, 10000)]

        tags = request.task.tags
        # Distinguish between only fetching the submitted_url vs all in the submission
        if not request.get_param('analyze_submitted_url'):
            # Only concerned with static/dynamic URIs found by prior services
            urls.extend(tags.get('network.static.uri', []) + tags.get('network.dynamic.uri', []))

        request.temp_submission_data.setdefault('visited_urls', {})

        # Headers that other AL services have sourced for fetching
        al_url_headers = request.temp_submission_data.get('url_headers', {})

        # Check if current file is malicious, if so tag URL that downloaded the file
        task_score = 0
        for tags_tuples in tags.values():
            task_score += sum([tag_tuple[1] for tag_tuple in tags_tuples])

        malicious_urls = []
        for url, hash in request.temp_submission_data['visited_urls'].items():
            if request.sha256 == hash and task_score >= 1000:
                malicious_urls.append(url)

        if malicious_urls:
            ResultSection("Malicious URLs Associated to File", body=json.dumps(malicious_urls),
                          tags={'network.static.uri': malicious_urls}, heuristic=Heuristic(1), parent=result)

        exception_table = ResultTableSection("Attempted Connection Exceptions")
        redirects_table = ResultTableSection("Connection History", heuristic=Heuristic(2))
        screenshot_section = ResultImageSection(request, title_text="Screenshots of visited pages")
        for tag_value, tag_score in sorted(urls, key=lambda x: x[1], reverse=True):
            # Minimize revisiting the same URIs in the same submission
            if tag_score < minimum_maliciousness:
                break

            if tag_value in request.temp_submission_data['visited_urls'].keys():
                continue

            headers = self.headers
            if request.get_param('user_agent'):
                headers['User-Agent'] = request.get_param('user_agent')

            headers.update(al_url_headers.get(tag_value, {}))
            # Write response and attach to submission
            sha256 = None
            try:
                self.log.debug(f'Trying {tag_value}')
                fp, sha256, history = self.fetch_uri(tag_value, headers=headers)
                if isinstance(fp, str):
                    if self.identify.fileinfo(fp)['type'] == 'code/html':
                        hti = Html2Image(browser='chrome', output_path=self.working_directory, custom_flags=[
                            '--hide-scrollbars',
                            '--no-sandbox'
                        ])
                        output_file = f"{tag_value.replace('/', '_')}.png"
                        # If identified to be an HTML document, render it and add to section
                        with NamedTemporaryFile(suffix=".html") as html_file:
                            html_file.write(open(fp, 'rb').read())
                            html_file.flush()
                            hti.screenshot(html_file=html_file.name, save_as=output_file)
                        screenshot_section.add_image(path=os.path.join(self.working_directory, output_file),
                                                     name=f'{tag_value}.png',
                                                     description=f"Screenshot of {tag_value}")

                    self.log.info(f'Success, writing to {fp}...')
                    if sha256 != request.sha256:
                        request.add_extracted(fp, tag_value, f"Response from {tag_value}",
                                              safelist_interface=self.api_interface)
                else:
                    self.log.debug(f'Server response except occurred: {fp.reason}')
                    exception_table.add_row(TableRow({'URI': tag_value, 'REASON': fp.reason}))

                if history:
                    redirects_table.add_row(TableRow({'URI': tag_value, 'HISTORY': ' → '.join(history)}))

            except Exception as e:
                if e.__class__ in REQUESTS_EXCEPTION_MSG:
                    exception_table.add_row(TableRow({'URI': tag_value, 'REASON': REQUESTS_EXCEPTION_MSG[e.__class__]}))
                else:
                    # Catch any except to ensure fetched files aren't lost due to arbitrary error
                    self.log.warning(f'General except occurred: {e}')
                    exception_table.add_row(TableRow({'URI': tag_value, 'REASON': str(e)}))
            finally:
                request.temp_submission_data['visited_urls'][tag_value] = sha256

        if screenshot_section.body:
            result.add_section(screenshot_section)
        if redirects_table.body:
            result.add_section(redirects_table)
        if exception_table.body:
            result.add_section(exception_table)

        request.result = result
