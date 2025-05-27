#!/bin/env python
import argparse
import hashlib
import json
import os
import shutil
from unittest.mock import patch

import pytest
import yaml
from assemblyline.common.importing import load_module_by_path
from assemblyline_service_utilities.testing.helper import TestHelper

cwd = os.getcwd()
# Force manifest location
os.environ["SERVICE_MANIFEST_PATH"] = os.path.join(cwd, "service_manifest.yml")

# Setup folder locations
RESULTS_FOLDER = os.path.join(cwd, "tests", "results")
SAMPLES_FOLDER = os.path.join(cwd, "tests", "samples")


# Find which module we're working on
module = os.environ.get("SERVICE_PATH")
if not module:
    for line in open("Dockerfile", "r").readlines():
        if line.startswith("ENV SERVICE_PATH"):
            module = line[17:].strip()
            break

# Initialize test helper
service_class = load_module_by_path(module, cwd)
if os.path.exists(SAMPLES_FOLDER):
    th = TestHelper(service_class, RESULTS_FOLDER, SAMPLES_FOLDER)
else:
    th = TestHelper(service_class, RESULTS_FOLDER)


kangooroo_parser = argparse.ArgumentParser()
kangooroo_parser.add_argument("-cf", "--conf-file", action="store", dest="conf")


def drop_kangooroo_files(sample, kangooroo_args, **kwargs):
    namespace, _ = kangooroo_parser.parse_known_args(kangooroo_args)
    with open(namespace.conf) as f:
        config = yaml.safe_load(f)

    kangooroo_input_path = os.path.join(RESULTS_FOLDER, sample, "kangooroo")
    with open(os.path.join(kangooroo_input_path, "results.json"), "r") as f:
        results = json.load(f)

    url_md5 = results["summary"]["requestedUrl"]["urlMd5"]
    output_folder = os.path.join(config["output_folder"], url_md5)
    shutil.copytree(src=kangooroo_input_path, dst=output_folder)


@pytest.mark.parametrize("sample", th.result_list())
@patch("subprocess.run")
def test_sample(mock_run, sample):
    def wrap_drop_kangooroo_files(*args, **kwargs):
        drop_kangooroo_files(sample, *args, **kwargs)

    mock_run.side_effect = wrap_drop_kangooroo_files
    th.regenerate_results(sample_sha256=sample)


pytest.main(["-p", "no:cacheprovider", "-rsx", "-vv", "tests/gentests.py::test_sample"])
