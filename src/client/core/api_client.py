import requests
import logging
from typing import List, Optional
from src.shared.schemas import Command, CommandResult, CommandStatus
from src.client.utils.hardware import get_system_info, get_hardware_id

logger = logging.getLogger(__name__)

class APIClient:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.session = requests.Session()
        self.device_pk: Optional[str] = None
        self.hardware_id = get_hardware_id()

    def register(self) -> bool:
        """Registers the device with the server."""
        payload = get_system_info()
        try:
            response = self.session.post(f"{self.base_url}/devices/", json=payload)
            if response.status_code in [200, 201]:
                data = response.json()
                self.device_pk = data.get('pk_device_id')
                logger.info(f"Registered device: {self.device_pk}")
                print(f"Registered/Connected: {self.device_pk}")
                return True
            else:
                logger.error(f"Registration failed: {response.text}")
                print(f"Registration failed: {response.text}")
                return False
        except Exception as e:
            logger.error(f"Connection error: {e}")
            print(f"Connection error during registration: {e}")
            return False

    def get_pending_commands(self) -> List[Command]:
        """Polls for pending commands."""
        if not self.device_pk:
            return []
        
        try:
            # We use hardware_id as lookup since we might not persist PK locally permanently yet
            response = self.session.get(
                f"{self.base_url}/commands/pending/", 
                params={"device_id": self.hardware_id} 
            )
            if response.status_code == 200:
                data = response.json()
                # Validate/Parse with Pydantic
                return [Command(**cmd) for cmd in data]
            return []
        except Exception as e:
            logger.error(f"Polling error: {e}")
            return []

    def update_command_status(self, command_id: str, result: CommandResult):
        """Updates command status on server."""
        try:
            payload = {
                "status": result.status,
                "log": {
                    "output": result.output,
                    "error_trace": result.error_trace
                }
            }
            # Using custom action 'result' as defined in existing views
            url = f"{self.base_url}/commands/{command_id}/result/"
            self.session.post(url, json=payload)
        except Exception as e:
            logger.error(f"Failed to update command status: {e}")
