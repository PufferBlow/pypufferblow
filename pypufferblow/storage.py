from __future__ import annotations

__all__ = [
    "Storage",
    "StorageOptions",
]

import requests
try:
    from loguru import logger
except ImportError:  # pragma: no cover - fallback for minimal SDK installs
    import logging

    logger = logging.getLogger(__name__)

from pypufferblow.exceptions import (
    BadAuthToken,
    FileNotFound,
    NotAnAdminOrServerOwner,
)
from pypufferblow.models.options_model import OptionsModel
from pypufferblow.models.route_model import Route
from pypufferblow.routes import storage_routes


class Storage:
    """
    Storage API wrapper for file uploads, metadata, and cleanup operations.

    This replaces the old CDN naming while keeping the same server routes.
    The API is intentionally instance-centric so it works for local, remote,
    and federated deployments that expose storage over the home instance API.
    """

    API_ROUTES: list[Route] = storage_routes

    UPLOAD_API_ROUTE: Route = storage_routes[0]
    LIST_FILES_API_ROUTE: Route = storage_routes[1]
    DELETE_FILE_API_ROUTE: Route = storage_routes[2]
    FILE_INFO_API_ROUTE: Route = storage_routes[3]
    CLEANUP_ORPHANED_API_ROUTE: Route = storage_routes[4]
    SERVE_FILE_API_ROUTE: Route = storage_routes[5]

    def __init__(self, options: StorageOptions) -> None:
        """Initialize the instance."""
        self.options = options
        self.host = options.host
        self.port = options.port
        self.instance = options.instance_url
        self.instance_url = options.instance_url
        self.auth_token = options.auth_token

    def upload_file(self, file_path: str, directory: str = "uploads") -> str:
        """
        Upload a file to instance storage.

        Args:
            file_path: Path to the file to upload.
            directory: Target storage directory/category.

        Returns:
            Canonical public storage URL, typically `/storage/<sha256>`.
        """
        logger.debug(
            f"Storage upload_file called with file_path='{file_path}', directory='{directory}'"
        )

        if not self._has_required_permissions():
            logger.warning("Storage upload_file failed: insufficient permissions")
            raise NotAnAdminOrServerOwner(
                "Storage file operations require admin or server owner privileges."
            )

        allowed_dirs = [
            "uploads",
            "avatars",
            "banners",
            "attachments",
            "stickers",
            "gifs",
            "images",
            "videos",
            "audio",
            "documents",
            "files",
            "config",
        ]
        if directory not in allowed_dirs:
            raise ValueError(f"Invalid directory. Allowed: {', '.join(allowed_dirs)}")

        try:
            with open(file_path, "rb") as file:
                files = {"file": (file.name, file)}
                data = {"auth_token": self.auth_token, "directory": directory}
                response = requests.post(
                    self.UPLOAD_API_ROUTE.api_route,
                    files=files,
                    data=data,
                )
        except IOError as exc:
            logger.error(
                f"Storage upload_file failed: could not open file '{file_path}': {exc}"
            )
            raise Exception(f"Could not open file: {file_path}") from exc

        self._raise_for_management_response(
            response=response,
            forbidden_message=(
                "Access forbidden. Only server owners can upload managed storage files."
            ),
            failure_message="File upload failed",
        )

        file_url = response.json().get("url")
        logger.info(f"Storage upload_file successful: file uploaded to {file_url}")
        return file_url

    def list_files(self, directory: str = "all") -> list[dict]:
        """List managed storage files."""
        if not self._has_required_permissions():
            raise NotAnAdminOrServerOwner(
                "Storage file operations require admin or server owner privileges."
            )

        response = requests.post(
            self.LIST_FILES_API_ROUTE.api_route,
            json={"auth_token": self.auth_token, "directory": directory},
        )
        self._raise_for_management_response(
            response=response,
            forbidden_message=(
                "Access forbidden. Only server owners can access managed storage."
            ),
        )
        return response.json().get("files", [])

    def delete_file(self, file_url: str) -> bool:
        """Delete a file from managed storage."""
        if not self._has_required_permissions():
            raise NotAnAdminOrServerOwner(
                "Storage file operations require admin or server owner privileges."
            )

        response = requests.post(
            self.DELETE_FILE_API_ROUTE.api_route,
            json={"auth_token": self.auth_token, "file_url": file_url},
        )

        if response.status_code == 400:
            if "not found" in response.text.lower():
                raise FileNotFound(f"File not found: {file_url}")
            raise BadAuthToken("Invalid auth token")
        if response.status_code == 403:
            if "forbidden" in response.text.lower():
                raise NotAnAdminOrServerOwner(
                    "Access forbidden. Only server owners can delete managed storage files."
                )
            raise Exception("Cannot delete protected file (avatar/banner in use)")
        if response.status_code == 404:
            raise FileNotFound(f"File not found: {file_url}")

        return response.status_code == 200

    def get_file_info(self, file_url: str) -> dict:
        """Get metadata about a managed storage file."""
        if not self._has_required_permissions():
            raise NotAnAdminOrServerOwner(
                "Storage file operations require admin or server owner privileges."
            )

        response = requests.post(
            self.FILE_INFO_API_ROUTE.api_route,
            json={"auth_token": self.auth_token, "file_url": file_url},
        )

        if response.status_code == 400:
            raise BadAuthToken("Invalid auth token")
        if response.status_code == 404:
            raise FileNotFound(f"File not found: {file_url}")

        return response.json().get("file_info", {})

    def cleanup_orphaned_files(self, directory: str = "") -> None:
        """Clean up unreferenced files in managed storage."""
        if not self._has_required_permissions():
            raise NotAnAdminOrServerOwner(
                "Storage cleanup operations require server owner privileges."
            )

        response = requests.post(
            self.CLEANUP_ORPHANED_API_ROUTE.api_route,
            json={"auth_token": self.auth_token, "subdirectory": directory},
        )
        self._raise_for_management_response(
            response=response,
            forbidden_message=(
                "Access forbidden. Only server owners can perform cleanup operations."
            ),
            failure_message="Cleanup operation failed",
        )

    def serve_file(self, file_path: str) -> bytes:
        """Fetch a file directly from storage."""
        params = {"auth_token": self.auth_token} if self.auth_token else {}
        base_route = self.SERVE_FILE_API_ROUTE.api_route.replace("{file_path:path}", "")
        response = requests.get(
            f"{base_route}{file_path.lstrip('/')}",
            params=params,
        )

        if response.status_code == 403:
            raise Exception("Access forbidden")
        if response.status_code == 404:
            raise FileNotFound(f"File not found: {file_path}")

        return response.content

    @staticmethod
    def _has_required_permissions() -> bool:
        """
        The server performs the authoritative privilege check.
        """
        return True

    @staticmethod
    def _raise_for_management_response(
        *,
        response,
        forbidden_message: str,
        failure_message: str | None = None,
    ) -> None:
        if response.status_code == 400:
            raise BadAuthToken("Invalid auth token")
        if response.status_code == 403:
            raise NotAnAdminOrServerOwner(forbidden_message)
        if response.status_code == 500 and failure_message:
            raise Exception(failure_message)


class StorageOptions(OptionsModel):
    """Options for configuring storage operations."""

    def __init__(self, auth_token: str, **kwargs):
        super().__init__(**kwargs)
        self.auth_token = auth_token
