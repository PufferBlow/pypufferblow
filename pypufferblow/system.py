__all__ = [
    "System",
    "SystemOptions"
]

import requests
from loguru import logger

# Routes
from pypufferblow.routes import system_routes

# Exceptions
from pypufferblow.exceptions import (
    BadAuthToken,
    NotAnAdminOrServerOwner,
    ServerError
)

# Models
from pypufferblow.models.route_model import Route
from pypufferblow.models.options_model import OptionsModel

class System: ...
class SystemOptions(OptionsModel): ...

class System:
    """
    The System class for system monitoring, information, and administration operations.

    Attributes:
        API_ROUTES (list[Route]): The list of the API routes.
        LATEST_RELEASE_API_ROUTE (Route): The latest release API route.
        SERVER_STATS_API_ROUTE (Route): The server stats API route.
        SERVER_INFO_API_ROUTE (Route): The server info API route.
        SERVER_USAGE_API_ROUTE (Route): The server usage API route.
        SERVER_OVERVIEW_API_ROUTE (Route): The server overview API route.
        ACTIVITY_METRICS_API_ROUTE (Route): The activity metrics API route.
        RECENT_ACTIVITY_API_ROUTE (Route): The recent activity API route.
        SERVER_LOGS_API_ROUTE (Route): The server logs API route.
        UPLOAD_AVATAR_API_ROUTE (Route): The upload server avatar API route.
        UPLOAD_BANNER_API_ROUTE (Route): The upload server banner API route.
        UPDATE_SERVER_INFO_API_ROUTE (Route): The update server info API route.
        USER_REGISTRATIONS_CHART_API_ROUTE (Route): The user registrations chart API route.
        MESSAGE_ACTIVITY_CHART_API_ROUTE (Route): The message activity chart API route.
        ONLINE_USERS_CHART_API_ROUTE (Route): The online users chart API route.
        CHANNEL_CREATION_CHART_API_ROUTE (Route): The channel creation chart API route.
        USER_STATUS_CHART_API_ROUTE (Route): The user status chart API route.
    """
    API_ROUTES: list[Route] = system_routes

    LATEST_RELEASE_API_ROUTE: Route = system_routes[0]
    SERVER_STATS_API_ROUTE: Route = system_routes[1]
    SERVER_INFO_API_ROUTE: Route = system_routes[2]
    SERVER_USAGE_API_ROUTE: Route = system_routes[3]
    SERVER_OVERVIEW_API_ROUTE: Route = system_routes[4]
    ACTIVITY_METRICS_API_ROUTE: Route = system_routes[5]
    RECENT_ACTIVITY_API_ROUTE: Route = system_routes[6]
    SERVER_LOGS_API_ROUTE: Route = system_routes[7]
    UPLOAD_AVATAR_API_ROUTE: Route = system_routes[8]
    UPLOAD_BANNER_API_ROUTE: Route = system_routes[9]
    UPDATE_SERVER_INFO_API_ROUTE: Route = system_routes[2]
    USER_REGISTRATIONS_CHART_API_ROUTE: Route = system_routes[10]
    MESSAGE_ACTIVITY_CHART_API_ROUTE: Route = system_routes[11]
    ONLINE_USERS_CHART_API_ROUTE: Route = system_routes[12]
    CHANNEL_CREATION_CHART_API_ROUTE: Route = system_routes[13]
    USER_STATUS_CHART_API_ROUTE: Route = system_routes[14]

    def __init__(self, options: SystemOptions) -> None:
        """
        Initialize the System object with the given options.

        Args:
            options (SystemOptions): The options for the System object.
        """
        self.options = options
        self.host = options.host
        self.port = options.port
        self.auth_token = options.auth_token

    def get_server_info(self) -> dict:
        """
        Get comprehensive server configuration information.

        Returns:
            dict: Server information including settings and configuration.

        Example:
            .. code-block:: python

                >>> server_info = client.system.get_server_info()
        """
        params = {"auth_token": self.auth_token}

        response = requests.get(
            self.SERVER_INFO_API_ROUTE.api_route,
            params=params
        )

        if response.status_code == 400:
            raise BadAuthToken("Invalid auth token")
        elif response.status_code != 200:
            raise ServerError("Failed to fetch server information")

        return response.json().get("server_info", {})

    def update_server_info(self, **kwargs) -> None:
        """
        Update server configuration settings. Server Owner only.

        Args:
            **kwargs: Server settings to update (server_name, server_description, is_private, etc.)

        Example:
            .. code-block:: python

                >>> client.system.update_server_info(server_name="My Server", server_description="A great server")
        """
        allowed_fields = [
            'server_name', 'server_description', 'is_private', 'max_users',
            'max_message_length', 'max_image_size', 'max_video_size',
            'max_sticker_size', 'max_gif_size'
        ]

        update_data = {}
        for field, value in kwargs.items():
            if field in allowed_fields:
                update_data[field] = value

        if not update_data:
            raise ValueError(f"No valid fields provided. Allowed: {', '.join(allowed_fields)}")

        payload = {"auth_token": self.auth_token, **update_data}

        response = requests.put(
            self.UPDATE_SERVER_INFO_API_ROUTE.api_route,
            json=payload
        )

        if response.status_code == 400:
            raise BadAuthToken("Invalid auth token")
        elif response.status_code == 403:
            raise NotAnAdminOrServerOwner("Access forbidden. Only server owners can update server settings.")
        elif response.status_code != 200:
            raise ServerError("Failed to update server information")

    def get_server_usage(self) -> dict:
        """
        Get real-time server usage statistics (CPU, RAM, storage).

        Returns:
            dict: Server usage metrics.

        Example:
            .. code-block:: python

                >>> usage = client.system.get_server_usage()
        """
        response = requests.post(self.SERVER_USAGE_API_ROUTE.api_route, json={})

        if response.status_code != 200:
            raise ServerError("Failed to fetch server usage statistics")

        return response.json().get("server_usage", {})

    def get_server_stats(self) -> dict:
        """
        Get comprehensive server statistics.

        Returns:
            dict: Server statistics including users, channels, messages.

        Example:
            .. code-block:: python

                >>> stats = client.system.get_server_stats()
        """
        params = {"auth_token": self.auth_token}

        response = requests.get(
            self.SERVER_STATS_API_ROUTE.api_route,
            params=params
        )

        if response.status_code == 400:
            raise BadAuthToken("Invalid auth token")

        return response.json().get("statistics", {})

    def get_server_overview(self) -> dict:
        """
        Get comprehensive server overview data for control panel.

        Returns:
            dict: Server overview statistics.

        Example:
            .. code-block:: python

                >>> overview = client.system.get_server_overview()
        """
        payload = {"auth_token": self.auth_token}

        response = requests.post(
            self.SERVER_OVERVIEW_API_ROUTE.api_route,
            json=payload
        )

        if response.status_code == 400:
            raise BadAuthToken("Invalid auth token")
        elif response.status_code == 403:
            raise NotAnAdminOrServerOwner("Access forbidden. Only administrators can access server overview.")

        return response.json().get("server_overview", {})

    def get_activity_metrics(self) -> dict:
        """
        Get current activity metrics for the control panel dashboard.

        Returns:
            dict: Activity metrics data.

        Example:
            .. code-block:: python

                >>> metrics = client.system.get_activity_metrics()
        """
        payload = {"auth_token": self.auth_token}

        response = requests.post(
            self.ACTIVITY_METRICS_API_ROUTE.api_route,
            json=payload
        )

        if response.status_code == 400:
            raise BadAuthToken("Invalid auth token")
        elif response.status_code == 403:
            raise NotAnAdminOrServerOwner("Access forbidden. Only administrators can access activity metrics.")

        return response.json().get("activity_metrics", {})

    def get_recent_activity(self, limit: int = 10) -> list[dict]:
        """
        Get recent activity events from the server.

        Args:
            limit (int): Maximum number of activities to return.

        Returns:
            list[dict]: List of recent activities.

        Example:
            .. code-block:: python

                >>> activities = client.system.get_recent_activity(limit=20)
        """
        payload = {
            "auth_token": self.auth_token,
            "limit": limit
        }

        response = requests.post(
            self.RECENT_ACTIVITY_API_ROUTE.api_route,
            json=payload
        )

        if response.status_code == 400:
            raise BadAuthToken("Invalid auth token")

        return response.json().get("activities", [])

    def get_server_logs(self, lines: int = 50, search: str = None, level: str = None) -> dict:
        """
        Get server logs with filtering options. Server Owner only.

        Args:
            lines (int): Number of log lines to return (max 1000).
            search (str): Search filter for log content.
            level (str): Log level filter (DEBUG, INFO, WARNING, ERROR, CRITICAL).

        Returns:
            dict: Server logs data.

        Example:
            .. code-block:: python

                >>> logs = client.system.get_server_logs(lines=100, level="ERROR")
        """
        if not self._has_required_permissions():
            raise NotAnAdminOrServerOwner("Access forbidden. Only server owners can access server logs.")

        payload = {
            "auth_token": self.auth_token,
            "lines": min(lines, 1000)
        }

        if search:
            payload["search"] = search
        if level:
            payload["level"] = level

        response = requests.post(
            self.SERVER_LOGS_API_ROUTE.api_route,
            json=payload
        )

        if response.status_code == 400:
            raise BadAuthToken("Invalid auth token")
        elif response.status_code == 403:
            raise NotAnAdminOrServerOwner("Access forbidden. Only server owners can access server logs.")
        elif response.status_code != 200:
            raise ServerError("Failed to fetch server logs")

        return response.json()

    def get_latest_release(self) -> dict:
        """
        Get information about the latest PufferBlow release.

        Returns:
            dict: Latest release information.

        Example:
            .. code-block:: python

                >>> release = client.system.get_latest_release()
        """
        response = requests.get(self.LATEST_RELEASE_API_ROUTE.api_route)

        if response.status_code == 200:
            return response.json().get("release", {})
        else:
            # Return fallback message if release info not available
            return {"message": "Release information not yet available"}

    def upload_server_avatar(self, avatar_file_path: str) -> str:
        """
        Upload server's avatar image. Server Owner only.

        Args:
            avatar_file_path (str): Path to the server avatar image file.

        Returns:
            str: The URL of the uploaded avatar.

        Example:
            .. code-block:: python

                >>> avatar_url = client.system.upload_server_avatar("/path/to/avatar.jpg")
        """
        logger.debug(f"System upload_server_avatar called with file_path='{avatar_file_path}'")

        if not self._has_required_permissions():
            logger.warning("System upload_server_avatar failed: insufficient permissions")
            raise NotAnAdminOrServerOwner("Access forbidden. Only server owners can update server avatar.")

        try:
            with open(avatar_file_path, 'rb') as file:
                files = {'avatar': (file.name, file, 'image/jpeg')}
                data = {'auth_token': self.auth_token}

                logger.debug(f"Making POST request to: {self.UPLOAD_AVATAR_API_ROUTE.api_route}")
                response = requests.post(
                    self.UPLOAD_AVATAR_API_ROUTE.api_route,
                    files=files,
                    data=data
                )

                logger.debug(f"Avatar upload response status: {response.status_code}")

        except IOError as e:
            logger.error(f"System upload_server_avatar failed: could not open file '{avatar_file_path}': {str(e)}")
            raise Exception(f"Could not open file: {avatar_file_path}")

        if response.status_code == 400:
            logger.warning("System upload_server_avatar failed: invalid auth token (400)")
            raise BadAuthToken("Invalid auth token")
        elif response.status_code == 403:
            logger.warning("System upload_server_avatar failed: forbidden access (403)")
            raise NotAnAdminOrServerOwner("Access forbidden. Only server owners can update server avatar.")
        elif response.status_code != 201:
            logger.error(f"System upload_server_avatar failed: server error ({response.status_code}) - Response: {response.text}")
            raise ServerError("Avatar upload failed")

        avatar_url = response.json().get("avatar_url")
        logger.info(f"System upload_server_avatar successful: avatar uploaded to {avatar_url}")
        return avatar_url

    def upload_server_banner(self, banner_file_path: str) -> str:
        """
        Upload server's banner image. Server Owner only.

        Args:
            banner_file_path (str): Path to the server banner image file.

        Returns:
            str: The URL of the uploaded banner.

        Example:
            .. code-block:: python

                >>> banner_url = client.system.upload_server_banner("/path/to/banner.jpg")
        """
        if not self._has_required_permissions():
            raise NotAnAdminOrServerOwner("Access forbidden. Only server owners can update server banner.")

        with open(banner_file_path, 'rb') as file:
            files = {'banner': (file.name, file, 'image/jpeg')}
            data = {'auth_token': self.auth_token}

            response = requests.post(
                self.UPLOAD_BANNER_API_ROUTE.api_route,
                files=files,
                data=data
            )

        if response.status_code == 400:
            raise BadAuthToken("Invalid auth token")
        elif response.status_code == 403:
            raise NotAnAdminOrServerOwner("Access forbidden. Only server owners can update server banner.")
        elif response.status_code != 201:
            raise ServerError("Banner upload failed")

        banner_url = response.json().get("banner_url")
        return banner_url

    # Chart methods
    def get_user_registration_chart(self, period: str = None) -> dict:
        """
        Get user registration chart data.

        Args:
            period (str): Time period (daily, weekly, monthly, 24h, 7d).

        Returns:
            dict: Chart data for user registrations.

        Example:
            .. code-block:: python

                >>> chart = client.system.get_user_registration_chart("weekly")
        """
        payload = {"auth_token": self.auth_token}
        if period:
            payload["period"] = period

        response = requests.post(
            self.USER_REGISTRATIONS_CHART_API_ROUTE.api_route,
            json=payload
        )

        if response.status_code == 400:
            raise BadAuthToken("Invalid auth token")

        return response.json().get("chart_data", {})

    def get_message_activity_chart(self, period: str = None) -> dict:
        """
        Get message activity chart data.

        Args:
            period (str): Time period.

        Returns:
            dict: Chart data for message activity.
        """
        payload = {"auth_token": self.auth_token}
        if period:
            payload["period"] = period

        response = requests.post(
            self.MESSAGE_ACTIVITY_CHART_API_ROUTE.api_route,
            json=payload
        )

        if response.status_code == 400:
            raise BadAuthToken("Invalid auth token")

        return response.json().get("chart_data", {})

    def get_online_users_chart(self, period: str = None) -> dict:
        """
        Get online users chart data.

        Args:
            period (str): Time period.

        Returns:
            dict: Chart data for online users.
        """
        payload = {"auth_token": self.auth_token}
        if period:
            payload["period"] = period

        response = requests.post(
            self.ONLINE_USERS_CHART_API_ROUTE.api_route,
            json=payload
        )

        if response.status_code == 400:
            raise BadAuthToken("Invalid auth token")

        return response.json().get("chart_data", {})

    def get_channel_creation_chart(self, period: str = None) -> dict:
        """
        Get channel creation chart data.

        Args:
            period (str): Time period.

        Returns:
            dict: Chart data for channel creation.
        """
        payload = {"auth_token": self.auth_token}
        if period:
            payload["period"] = period

        response = requests.post(
            self.CHANNEL_CREATION_CHART_API_ROUTE.api_route,
            json=payload
        )

        if response.status_code == 400:
            raise BadAuthToken("Invalid auth token")

        return response.json().get("chart_data", {})

    def get_user_status_chart(self) -> dict:
        """
        Get user status distribution chart data.

        Returns:
            dict: Chart data for user status distribution.
        """
        payload = {"auth_token": self.auth_token}

        response = requests.post(
            self.USER_STATUS_CHART_API_ROUTE.api_route,
            json=payload
        )

        if response.status_code == 400:
            raise BadAuthToken("Invalid auth token")

        return response.json().get("chart_data", {})

    def _has_required_permissions(self) -> bool:
        """
        Check if the current user has required permissions for admin operations.
        This is a basic check - the server will do the actual validation.
        """
        return True


class SystemOptions(OptionsModel):
    """
    System options for configuring system operations.
    """
    def __init__(self, auth_token: str, **kwargs):
        super().__init__(**kwargs)
        self.auth_token = auth_token
