import requests

from assemblyline_v4_service.common.base import ServiceBase
from assemblyline_v4_service.common.request import ServiceRequest
from assemblyline_v4_service.common.result import Result, ResultTableSection, TableRow

from tempfile import NamedTemporaryFile
from typing import Union


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
            resp_fh.write(requests.get(uri, allow_redirects=True, headers=headers, timeout=self.timeout).content)
            resp_fh.close()
            return resp_fh.name
        return resp

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

        request.temp_submission_data.setdefault('visited_urls', [])
        exception_table = ResultTableSection("Attempted Connection Exceptions")
        for tag_value, tag_score in sorted(urls, key=lambda x: x[1], reverse=True):
            # Minimize revisiting the same URIs in the same submission
            if tag_score < minimum_maliciousness:
                break

            if tag_value in request.temp_submission_data['visited_urls']:
                continue

            request.temp_submission_data['visited_urls'].append(tag_value)
            # Write response and attach to submission
            try:
                self.log.debug(f'Trying {tag_value}')
                fp = self.fetch_uri(tag_value, headers=headers)
                if isinstance(fp, str):
                    self.log.info(f'Success, writing to {fp}...')
                    request.add_extracted(fp, tag_value, f"Response from {tag_value}",
                                          safelist_interface=self.api_interface)
                else:
                    self.log.debug(f'Server response exception occurred: {e}')
                    exception_table.add_row(TableRow({'URI': tag_value, 'REASON': fp.reason}))
            except requests.exceptions.ConnectionError as e:
                self.log.debug(f'ConnectionError exception occurred: {e}')
                exception_table.add_row(TableRow({'URI': tag_value, 'REASON': str(e).split(':')[-1][:-2]}))
            except requests.exceptions.ReadTimeout as e:
                self.log.debug(f'ReadTimeout exception occurred: {e}')
                if self.proxy and any([proxy in str(e) for proxy in self.proxy.values()]):
                    exception_table.add_row(
                        TableRow({'URI': tag_value, 'REASON': 'Problem using proxy to reach destination.'}))
                else:
                    exception_table.add_row(TableRow({'URI': tag_value, 'REASON': str(e).split(':')[-1][:-2]}))
            except Exception as e:
                self.log.debug(f'General exception occurred: {e}')
                # Catch any exception to ensure fetched files aren't lost due to arbitrary error
                exception_table.add_row(TableRow({'URI': tag_value, 'REASON': str(e).split(':')[-1][:-2]}))

        if exception_table.body:
            result.add_section(exception_table)

        request.result = result
