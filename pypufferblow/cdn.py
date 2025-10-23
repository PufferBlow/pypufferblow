__all__ = [
    "CDN",
    "CDNOptions"
]

import requests
from loguru import logger

# Routes
from pypufferblow.routes import cdn_routes

# Exceptions
from pypufferblow.exceptions import (
    BadAuthToken,
    NotAnAdminOrServerOwner,
    FileNotFound,
    UnsupportedFileType
)

# Models
from pypufferblow.models.route_model import Route
from pypufferblow.models.options_model import OptionsModel

class CDN: ...
class CDNOptions(OptionsModel): ...

class CDN:
    """
    The CDN class for managing file uploads, downloads, and management operations.

    Attributes:
        API_ROUTES (list[Route]): The list of the API routes.
        UPLOAD_API_ROUTE (Route): The upload file API route.
        LIST_FILES_API_ROUTE (Route): The list files API route.
        DELETE_FILE_API_ROUTE (Route): The delete file API route.
        FILE_INFO_API_ROUTE (Route): The file info API route.
        CLEANUP_ORPHANED_API_ROUTE (Route): The cleanup orphaned files API route.
        SERVE_FILE_API_ROUTE (Route): The serve file API route.
    """
    API_ROUTES: list[Route] = cdn_routes

    UPLOAD_API_ROUTE: Route = cdn_routes[0]
    LIST_FILES_API_ROUTE: Route = cdn_routes[1]
    DELETE_FILE_API_ROUTE: Route = cdn_routes[2]
    FILE_INFO_API_ROUTE: Route = cdn_routes[3]
    CLEANUP_ORPHANED_API_ROUTE: Route = cdn_routes[4]
    SERVE_FILE_API_ROUTE: Route = cdn_routes[5]

    def __init__(self, options: CDNOptions) -> None:
        """
        Initialize the CDN object with the given options.

        Args:
            options (CDNOptions): The options for the CDN object.
        """
        self.options = options
        self.host = options.host
        self.port = options.port
        self.auth_token = options.auth_token

    def upload_file(self, file_path: str, directory: str = "uploads") -> str:
        """
        Upload a file to the CDN.

        Args:
            file_path (str): Path to the file to upload.
            directory (str): Target directory (uploads, avatars, banners, attachments, stickers, gifs).

        Returns:
            str: The URL of the uploaded file.

        Example:
            .. code-block:: python

                >>> file_url = client.cdn.upload_file("/path/to/file.jpg", directory="avatars")
        """
        logger.debug(f"CDN upload_file called with file_path='{file_path}', directory='{directory}'")

        if not self._has_required_permissions():
            logger.warning("CDN upload_file failed: insufficient permissions")
            raise NotAnAdminOrServerOwner("CDN file operations require admin or server owner privileges.")

        allowed_dirs = ['uploads', 'avatars', 'banners', 'attachments', 'stickers', 'gifs']
        if directory not in allowed_dirs:
            logger.error(f"CDN upload_file failed: invalid directory '{directory}'")
            raise ValueError(f"Invalid directory. Allowed: {', '.join(allowed_dirs)}")

        try:
            with open(file_path, 'rb') as file:
                files = {'file': (file.name, file)}
                data = {'auth_token': self.auth_token, 'directory': directory}

                logger.debug(f"Making POST request to: {self.UPLOAD_API_ROUTE.api_route}")
                response = requests.post(
                    self.UPLOAD_API_ROUTE.api_route,
                    files=files,
                    data=data
                )

                logger.debug(f"File upload response status: {response.status_code}")

        except IOError as e:
            logger.error(f"CDN upload_file failed: could not open file '{file_path}': {str(e)}")
            raise Exception(f"Could not open file: {file_path}")

        if response.status_code == 400:
            logger.warning("CDN upload_file failed: invalid auth token (400)")
            raise BadAuthToken("Invalid auth token")
        elif response.status_code == 403:
            logger.warning("CDN upload_file failed: forbidden access (403)")
            raise NotAnAdminOrServerOwner("Access forbidden. Only server owners can upload CDN files.")
        elif response.status_code == 500:
            logger.error(f"CDN upload_file failed: server error (500) - Response: {response.text}")
            raise Exception("File upload failed")

        file_url = response.json().get("url")
        logger.info(f"CDN upload_file successful: file uploaded to {file_url}")
        return file_url

    def list_files(self, directory: str = "all") -> list[dict]:
        """
        List files in a CDN directory.

        Args:
            directory (str): Directory to list files from.

        Returns:
            list[dict]: List of file information.

        Example:
            .. code-block:: python

                >>> files = client.cdn.list_files("avatars")
        """
        if not self._has_required_permissions():
            raise NotAnAdminOrServerOwner("CDN file operations require admin or server owner privileges.")

        params = {
            "auth_token": self.auth_token,
            "directory": directory
        }

        response = requests.get(
            self.LIST_FILES_API_ROUTE.api_route,
            params=params
        )

        if response.status_code == 400:
            raise BadAuthToken("Invalid auth token")
        elif response.status_code == 403:
            raise NotAnAdminOrServerOwner("Access forbidden. Only server owners can access CDN management.")

        files_data = response.json().get("files", [])
        return files_data

    def delete_file(self, file_url: str) -> bool:
        """
        Delete a file from the CDN.

        Args:
            file_url (str): URL of the file to delete.

        Returns:
            bool: True if deleted successfully.

        Example:
            .. code-block:: python

                >>> client.cdn.delete_file("https://cdn.example.com/uploads/file.jpg")
        """
        if not self._has_required_permissions():
            raise NotAnAdminOrServerOwner("CDN file operations require admin or server owner privileges.")

        params = {
            "auth_token": self.auth_token,
            "file_url": file_url
        }

        response = requests.post(
            self.DELETE_FILE_API_ROUTE.api_route,
            params=params
        )

        if response.status_code == 400:
            if "not found" in response.text.lower():
                raise FileNotFound(f"File not found: {file_url}")
            raise BadAuthToken("Invalid auth token")
        elif response.status_code == 403:
            if "forbidden" in response.text.lower():
                raise NotAnAdminOrServerOwner("Access forbidden. Only server owners can delete CDN files.")
            raise Exception("Cannot delete protected file (avatar/banner in use)")
        elif response.status_code == 404:
            raise FileNotFound(f"File not found: {file_url}")

        return response.status_code == 200

    def get_file_info(self, file_url: str) -> dict:
        """
        Get information about a specific file.

        Args:
            file_url (str): URL of the file to get info about.

        Returns:
            dict: File information.

        Example:
            .. code-block:: python

                >>> info = client.cdn.get_file_info("https://cdn.example.com/uploads/file.jpg")
        """
        if not self._has_required_permissions():
            raise NotAnAdminOrServerOwner("CDN file operations require admin or server owner privileges.")

        params = {
            "auth_token": self.auth_token,
            "file_url": file_url
        }

        response = requests.get(
            self.FILE_INFO_API_ROUTE.api_route,
            params=params
        )

        if response.status_code == 400:
            raise BadAuthToken("Invalid auth token")
        elif response.status_code == 404:
            raise FileNotFound(f"File not found: {file_url}")

        return response.json().get("file_info", {})

    def cleanup_orphaned_files(self, directory: str = "") -> None:
        """
        Clean up orphaned files that are no longer referenced.

        Args:
            directory (str): Directory to clean (defaults to all supported directories).

        Example:
            .. code-block:: python

                >>> client.cdn.cleanup_orphaned_files("avatars")
        """
        if not self._has_required_permissions():
            raise NotAnAdminOrServerOwner("CDN cleanup operations require server owner privileges.")

        params = {
            "auth_token": self.auth_token,
            "subdirectory": directory
        }

        response = requests.post(
            self.CLEANUP_ORPHANED_API_ROUTE.api_route,
            params=params
        )

        if response.status_code == 400:
            raise BadAuthToken("Invalid auth token")
        elif response.status_code == 403:
            raise NotAnAdminOrServerOwner("Access forbidden. Only server owners can perform cleanup operations.")
        elif response.status_code == 500:
            raise Exception("Cleanup operation failed")

    def serve_file(self, file_path: str) -> bytes:
        """
        Serve a file directly from CDN (for authenticated access).

        Args:
            file_path (str): Relative path of the file.

        Returns:
            bytes: File content.

        Example:
            .. code-block:: python

                >>> content = client.cdn.serve_file("uploads/file.jpg")
        """
        params = {"auth_token": self.auth_token} if self.auth_token else {}

        response = requests.get(
            f"{self.SERVE_FILE_API_ROUTE.api_route.rstrip('{file_path:path}')}{file_path}",
            params=params
        )

        if response.status_code == 403:
            raise Exception("Access forbidden")
        elif response.status_code == 404:
            raise FileNotFound(f"File not found: {file_path}")

        return response.content

    def _has_required_permissions(self) -> bool:
        """
        Check if the current user has required permissions for CDN operations.
        This is a basic check - the server will do the actual validation.
        """
        # This would typically check user roles, but for now we rely on server validation
        return True


class CDNOptions(OptionsModel):
    """
    CDN options for configuring CDN operations.
    """
    def __init__(self, auth_token: str, **kwargs):
        super().__init__(**kwargs)
        self.auth_token = auth_token
