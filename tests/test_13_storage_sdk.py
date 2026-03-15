from __future__ import annotations

import tempfile
from pathlib import Path

from pypufferblow.client import Client, ClientOptions
from pypufferblow.storage import Storage


def create_authenticated_client(mock_sdk_backend) -> Client:
    auth_token = mock_sdk_backend.seed_user(username="user1", password="12345678")
    client = Client(
        ClientOptions(
            instance="https://chat.example.org",
            username="user1",
            password="12345678",
        )
    )
    client.users.user.auth_token = auth_token
    client.users.is_signed_in = True
    return client


def test_storage_object_routes(mock_sdk_backend) -> None:
    client = create_authenticated_client(mock_sdk_backend)

    storage = client.storage()

    assert isinstance(storage, Storage)
    assert storage.UPLOAD_API_ROUTE.api_route == "https://chat.example.org/api/v1/storage/upload"


def test_storage_management_operations(mock_sdk_backend) -> None:
    client = create_authenticated_client(mock_sdk_backend)
    storage = client.storage()

    with tempfile.TemporaryDirectory() as temp_dir:
        file_path = Path(temp_dir) / "avatar.png"
        file_path.write_bytes(b"storage-test-content")

        file_url = storage.upload_file(str(file_path), directory="avatars")
        files = storage.list_files("avatars")
        file_info = storage.get_file_info(file_url)
        deleted = storage.delete_file(file_url)

    assert file_url.startswith("/storage/")
    assert len(files) == 1
    assert files[0]["url"] == file_url
    assert file_info["url"] == file_url
    assert deleted is True
