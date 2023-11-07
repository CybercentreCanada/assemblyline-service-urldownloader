#!/bin/env python
import hashlib
import os
import shutil
from unittest.mock import patch

import pytest
import yaml
from assemblyline.common.importing import load_module_by_path
from assemblyline_service_utilities.testing.helper import TestHelper

# Force manifest location
os.environ["SERVICE_MANIFEST_PATH"] = os.path.join(os.path.dirname(__file__), "..", "service_manifest.yml")

# Setup folder locations
RESULTS_FOLDER = os.path.join(os.path.dirname(__file__), "results")

# Initialize test helper
service_class = load_module_by_path("urldownloader.URLDownloader", os.path.join(os.path.dirname(__file__), ".."))
th = TestHelper(service_class, RESULTS_FOLDER)


def drop_kangooroo_files(sample, kangooroo_args, **kwargs):
    config_path = kangooroo_args[5]  # Assume it's 5 for now
    uri = kangooroo_args[-1]  # Assume it's -1 for now
    with open(config_path) as f:
        config = yaml.safe_load(f)

    url_md5 = hashlib.md5(uri.encode()).hexdigest()
    output_folder = os.path.join(config["output_folder"], url_md5)
    kangooroo_input_path = os.path.join(RESULTS_FOLDER, sample, "kangooroo")
    shutil.copytree(src=kangooroo_input_path, dst=output_folder)


@pytest.mark.parametrize("sample", th.result_list())
@patch("urldownloader.subprocess.run")
def test_sample(mock_run, sample):
    def wrap_drop_kangooroo_files(*args, **kwargs):
        drop_kangooroo_files(sample, *args, **kwargs)

    mock_run.side_effect = wrap_drop_kangooroo_files
    th.regenerate_results(sample_sha256=sample)


pytest.main(["-p", "no:cacheprovider", "-rsx", "-vv", "tests/gentests.py::test_sample"])
