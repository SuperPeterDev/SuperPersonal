import uuid
import socket
import platform
import logging

logger = logging.getLogger(__name__)

def get_hardware_id() -> str:
    """Returns a unique hardware ID based on MAC address."""
    return str(uuid.getnode())

def get_system_info() -> dict:
    """Returns system information."""
    return {
        "hardware_id": get_hardware_id(),
        "hostname": socket.gethostname(),
        "os_config": {
            "system": platform.system(),
            "release": platform.release(),
            "version": platform.version()
        }
    }
