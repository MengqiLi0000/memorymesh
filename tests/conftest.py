import os, pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="session")
def app_client(tmp_path_factory):
    os.environ["MESH_DATA_DIR"] = str(tmp_path_factory.mktemp("mesh"))
    os.environ.setdefault("MESH_LLM_PROVIDER", "none")
    os.environ["MESH_ADMIN_KEY"] = "test-admin-key"
    from memory_mesh.api import create_app
    with TestClient(create_app()) as c:
        yield c


@pytest.fixture(scope="session")
def mk(app_client):
    from memory_mesh_sdk import MemoryMesh

    def make(key):
        m = MemoryMesh(api_key=key, base_url="http://testserver")
        m._http = app_client
        app_client.headers.pop("Authorization", None)
        orig = m._req

        def req(method, path, json=None, params=None):
            r = app_client.request(method, path, json=json, params=params, headers={"Authorization": f"Bearer {key}"})
            body = r.json() if r.content else None
            if r.status_code >= 400:
                from memory_mesh_sdk import MeshAPIError
                raise MeshAPIError(r.status_code, body)
            return body
        m._req = req
        return m
    return make


@pytest.fixture(scope="session")
def owner(mk):
    return mk("test-admin-key")
