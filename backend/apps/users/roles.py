"""
Admin Roles and Permissions Configuration

This module defines the role-based access control (RBAC) for the IoT Hub admin interface.
"""

from enum import Enum


class AdminRole(Enum):
    """
    Admin roles with their capabilities.

    Each role maps to a Django Group with specific permissions.
    """

    SUPERUSER = "superuser"
    ADMIN = "admin"
    OPERATOR = "operator"
    VIEWER = "viewer"


# Role capabilities documentation
ROLE_CAPABILITIES = {
    "superuser": {
        "description": "Full system access with no restrictions",
        "can_view": ["all"],
        "can_add": ["all"],
        "can_change": ["all"],
        "can_delete": ["all"],
        "can_access_admin": True,
        "special_permissions": [
            "Create/delete users",
            "Modify Django settings",
            "Access all admin actions",
            "Bypass all permission checks",
        ],
        "typical_users": ["System administrators", "DevOps engineers"],
    },
    "admin": {
        "description": "Full access to IoT Hub models and data",
        "can_view": ["Device", "Telemetry", "Metric", "DeviceMetric", "Rule", "Event"],
        "can_add": ["Device", "Telemetry", "Metric", "DeviceMetric", "Rule", "Event"],
        "can_change": ["Device", "Telemetry", "Metric", "DeviceMetric", "Rule", "Event"],
        "can_delete": ["Device", "Telemetry", "Metric", "DeviceMetric", "Rule", "Event"],
        "can_access_admin": True,
        "special_permissions": [
            "Bulk operations on devices",
            "Delete telemetry data",
            "Modify rules and events",
        ],
        "typical_users": ["IoT platform administrators", "Data managers"],
    },
    "operator": {
        "description": "Can view, add, and modify data but cannot delete",
        "can_view": ["Device", "Telemetry", "Metric", "DeviceMetric", "Rule", "Event"],
        "can_add": ["Device", "Telemetry", "Metric", "DeviceMetric", "Rule", "Event"],
        "can_change": ["Device", "Telemetry", "Metric", "DeviceMetric", "Rule", "Event"],
        "can_delete": [],
        "can_access_admin": True,
        "special_permissions": [
            "Activate/deactivate devices",
            "Create and modify rules",
            "Add telemetry data manually",
        ],
        "typical_users": ["Device operators", "Support engineers", "IoT technicians"],
    },
    "viewer": {
        "description": "Read-only access to all IoT Hub data",
        "can_view": ["Device", "Telemetry", "Metric", "DeviceMetric", "Rule", "Event"],
        "can_add": [],
        "can_change": [],
        "can_delete": [],
        "can_access_admin": True,
        "special_permissions": ["Export data to CSV", "View dashboards and reports"],
        "typical_users": ["Analysts", "Auditors", "Stakeholders", "Clients"],
    },
}


def get_role_capabilities(role_name):
    """
    Get capabilities for a specific role.

    Args:
        role_name (str): Name of the role (superuser, admin, operator, viewer)

    Returns:
        dict: Role capabilities or None if role doesn't exist
    """
    return ROLE_CAPABILITIES.get(role_name.lower())


def print_role_summary():
    """Print a formatted summary of all roles and their capabilities."""
    print("\n" + "=" * 80)
    print("IoT Hub Admin - Role Capabilities Summary")
    print("=" * 80 + "\n")

    for role_name, capabilities in ROLE_CAPABILITIES.items():
        print(f"Role: {role_name.upper()}")
        print(f"Description: {capabilities['description']}")
        print(f"Can Access Admin: {capabilities['can_access_admin']}")

        if capabilities['can_view']:
            print(f"  View: {', '.join(capabilities['can_view'])}")
        if capabilities['can_add']:
            print(f"  Add: {', '.join(capabilities['can_add'])}")
        if capabilities['can_change']:
            print(f"  Change: {', '.join(capabilities['can_change'])}")
        if capabilities['can_delete']:
            print(f"  Delete: {', '.join(capabilities['can_delete'])}")

        if capabilities['special_permissions']:
            print(f"  Special Permissions:")
            for perm in capabilities['special_permissions']:
                print(f"    - {perm}")

        print(f"  Typical Users: {', '.join(capabilities['typical_users'])}")
        print("\n" + "-" * 80 + "\n")


if __name__ == "__main__":
    print_role_summary()
