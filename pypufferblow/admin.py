__all__ = [
    "Admin",
    "AdminOptions"
]

import requests
from loguru import logger

# Routes
from pypufferblow.routes import admin_routes

# Exceptions
from pypufferblow.exceptions import (
    BadAuthToken,
    NotAnAdminOrServerOwner,
    IPSecurityError
)

# Models
from pypufferblow.models.route_model import Route
from pypufferblow.models.options_model import OptionsModel

class Admin: ...
class AdminOptions(OptionsModel): ...

class Admin:
    """
    The Admin class for administration operations requiring elevated permissions.

    Attributes:
        API_ROUTES (list[Route]): The list of the API routes.
        LIST_BLOCKED_IPS_API_ROUTE (Route): The list blocked IPs route.
        BLOCK_IP_API_ROUTE (Route): The block IP route.
        UNBLOCK_IP_API_ROUTE (Route): The unblock IP route.
        BACKGROUND_TASKS_STATUS_API_ROUTE (Route): The background tasks status route.
        BACKGROUND_TASKS_RUN_API_ROUTE (Route): The background tasks run route.
    """
    API_ROUTES: list[Route] = admin_routes

    LIST_BLOCKED_IPS_API_ROUTE: Route = admin_routes[0]
    BLOCK_IP_API_ROUTE: Route = admin_routes[1]
    UNBLOCK_IP_API_ROUTE: Route = admin_routes[2]
    BACKGROUND_TASKS_STATUS_API_ROUTE: Route = admin_routes[3]
    BACKGROUND_TASKS_RUN_API_ROUTE: Route = admin_routes[4]

    def __init__(self, options: AdminOptions) -> None:
        """
        Initialize the Admin object with the given options.

        Args:
            options (AdminOptions): The options for the Admin object.
        """
        self.options = options
        self.host = options.host
        self.port = options.port
        self.auth_token = options.auth_token

    def list_blocked_ips(self) -> list[dict]:
        """
        List all blocked IPs with details. Server Owner only.

        Returns:
            list[dict]: List of blocked IP information.

        Example:
            .. code-block:: python

                >>> blocked_ips = client.admin.list_blocked_ips()
        """
        if not self._has_required_permissions():
            raise NotAnAdminOrServerOwner("Access forbidden. Only server owners can manage blocked IPs.")

        params = {"auth_token": self.auth_token}

        response = requests.get(
            self.LIST_BLOCKED_IPS_API_ROUTE.api_route,
            params=params
        )

        if response.status_code == 400:
            raise BadAuthToken("Invalid auth token")
        elif response.status_code == 403:
            raise NotAnAdminOrServerOwner("Access forbidden. Only server owners can manage blocked IPs.")
        elif response.status_code != 200:
            raise IPSecurityError("Failed to list blocked IPs")

        return response.json().get("blocked_ips", [])

    def block_ip(self, ip: str, reason: str) -> None:
        """
        Add an IP address to the blocked list. Server Owner only.

        Args:
            ip (str): IP address to block (IPv4 or IPv6).
            reason (str): Reason for blocking the IP.

        Example:
            .. code-block:: python

                >>> client.admin.block_ip("192.168.1.100", "Suspicious activity")
        """
        if not self._has_required_permissions():
            raise NotAnAdminOrServerOwner("Access forbidden. Only server owners can manage blocked IPs.")

        params = {
            "auth_token": self.auth_token,
            "ip": ip,
            "reason": reason
        }

        response = requests.post(
            self.BLOCK_IP_API_ROUTE.api_route,
            params=params
        )

        if response.status_code == 400:
            if "already blocked" in response.text.lower():
                raise IPSecurityError(f"IP {ip} is already blocked")
            elif "format" in response.text.lower():
                raise ValueError(f"Invalid IP address format: {ip}")
            raise BadAuthToken("Invalid auth token")
        elif response.status_code == 403:
            raise NotAnAdminOrServerOwner("Access forbidden. Only server owners can manage blocked IPs.")
        elif response.status_code != 201:
            raise IPSecurityError("Failed to block IP address")

    def unblock_ip(self, ip: str) -> None:
        """
        Remove an IP address from the blocked list. Server Owner only.

        Args:
            ip (str): IP address to unblock.

        Example:
            .. code-block:: python

                >>> client.admin.unblock_ip("192.168.1.100")
        """
        if not self._has_required_permissions():
            raise NotAnAdminOrServerOwner("Access forbidden. Only server owners can manage blocked IPs.")

        params = {
            "auth_token": self.auth_token,
            "ip": ip
        }

        response = requests.post(
            self.UNBLOCK_IP_API_ROUTE.api_route,
            params=params
        )

        if response.status_code == 400:
            if "not blocked" in response.text.lower():
                raise IPSecurityError(f"IP {ip} is not currently blocked")
            raise BadAuthToken("Invalid auth token")
        elif response.status_code == 403:
            raise NotAnAdminOrServerOwner("Access forbidden. Only server owners can manage blocked IPs.")
        elif response.status_code != 200:
            raise IPSecurityError("Failed to unblock IP address")

    def get_background_tasks_status(self) -> dict:
        """
        Get status of all background tasks. Server Owner only.

        Returns:
            dict: Background tasks status information.

        Example:
            .. code-block:: python

                >>> status = client.admin.get_background_tasks_status()
        """
        if not self._has_required_permissions():
            raise NotAnAdminOrServerOwner("Access forbidden. Only server owners can manage background tasks.")

        params = {"auth_token": self.auth_token}

        response = requests.get(
            self.BACKGROUND_TASKS_STATUS_API_ROUTE.api_route,
            params=params
        )

        if response.status_code == 400:
            raise BadAuthToken("Invalid auth token")
        elif response.status_code == 403:
            raise NotAnAdminOrServerOwner("Access forbidden. Only server owners can manage background tasks.")

        return response.json().get("tasks", {})

    def run_background_task(self, task_id: str) -> dict:
        """
        Execute a background task on-demand. Server Owner only.

        Args:
            task_id (str): ID of the background task to run.

        Returns:
            dict: Task execution result.

        Example:
            .. code-block:: python

                >>> result = client.admin.run_background_task("cleanup_old_logs")
        """
        if not self._has_required_permissions():
            raise NotAnAdminOrServerOwner("Access forbidden. Only server owners can manage background tasks.")

        params = {
            "auth_token": self.auth_token,
            "task_id": task_id
        }

        response = requests.post(
            self.BACKGROUND_TASKS_RUN_API_ROUTE.api_route,
            params=params
        )

        if response.status_code == 400:
            if "not found" in response.text.lower() or task_id in response.text.lower():
                raise ValueError(f"Background task '{task_id}' not found")
            elif "not initialized" in response.text.lower():
                raise IPSecurityError("Background tasks manager not initialized")
            raise BadAuthToken("Invalid auth token")
        elif response.status_code == 403:
            raise NotAnAdminOrServerOwner("Access forbidden. Only server owners can manage background tasks.")
        elif response.status_code != 200:
            raise IPSecurityError(f"Failed to execute background task: {task_id}")

        return {
            "task_id": task_id,
            "status": "executed",
            "message": f"Background task '{task_id}' executed successfully"
        }

    def _has_required_permissions(self) -> bool:
        """
        Check if the current user has required permissions for admin operations.
        This is a basic check - the server will do the actual validation.
        """
        return True


class AdminOptions(OptionsModel):
    """
    Admin options for configuring admin operations.
    """
    def __init__(self, auth_token: str, **kwargs):
        super().__init__(**kwargs)
        self.auth_token = auth_token
