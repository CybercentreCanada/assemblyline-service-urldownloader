import requests

from assemblyline_v4_service.common.base import ServiceBase
from assemblyline_v4_service.common.request import ServiceRequest
from assemblyline_v4_service.common.result import Result

from tempfile import NamedTemporaryFile


class URLDownloader(ServiceBase):
    def __init__(self, config) -> None:
        super().__init__(config)
        self.content_type_filter: list = config.get('content_type_filter', [])
        self.content_type_filter.append(None)

    def fetch_uri(self, uri: str, apply_filter: bool = True) -> str:
        try:
            resp = requests.get(uri, allow_redirects=True)
            # Only concerned with gathering responses of interest
            if resp.ok:
                if apply_filter and resp.headers.get('Content-Type') in self.content_type_filter:
                    return
                resp_fh = NamedTemporaryFile(delete=False)
                resp_fh.write(resp.content)
                resp_fh.close()
                return resp_fh.name
        except:
            pass
        return

    def execute(self, request: ServiceRequest) -> None:
        result = Result()
        submitted_url = []

        # Code to be used when responsibility of fetching submitted_url is moved to service from UI
        # -----------------------------------------------------------------------------------------
        # submitted_url = request.task.metadata.get('submitted_url')
        # # Make sure this is the first URL fetched
        # submitted_url = [(submitted_url, 10000)] if submitted_url and request.task.depth == 0 else []

        # Only concerned with static/dynamic URIs found by prior services
        tags = request.task.tags
        urls = tags.get('network.static.uri', []) + tags.get('network.dynamic.uri', []) + submitted_url

        for tag_value, tag_score in sorted(urls, key=lambda x: x[1]):
            # Write response and attach to submission
            fp = self.fetch_uri(tag_value, apply_filter=bool(tag_score < 500))
            request.add_extracted(fp, tag_value, f"Response from {tag_value}",
                                  safelist_interface=self.api_interface) if fp else None

        request.result = result
