import pytest
from ml_models.serving.service import ModelService


@pytest.fixture(scope="session")
def trained_service(tmp_path_factory):
    service = ModelService(tmp_path_factory.mktemp("models"))
    service.bootstrap("quick")
    return service
