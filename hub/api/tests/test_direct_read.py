import json
from hub.tests.storage_fixtures import enabled_storages, enabled_persistent_storages
import os
import pytest

file_to_upload = "Hub/hub/tests/dummy_data/images/cat.jpeg"

def check_direct_read(storage):

    # upload the file to storage using url and fetching it using hub.read using cloud url
    assert type(sample.array) == numpy.ndarray
    assert sample.compression == "jpeg"

@enabled_storages
def test_direct_read(storage):
    check_direct_read(storage)