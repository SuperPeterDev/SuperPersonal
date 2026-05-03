import logging
import sys
from src.client.core.executor import CommandExecutor
from src.client.core.registry import ExecutorRegistry
from src.shared.schemas import CommandPayload, CommandResult
from src.shared.enums import CommandType, CommandStatus

logger = logging.getLogger(__name__)

@ExecutorRegistry.register(CommandType.CMD_SET_VOLUME)
class VolumeExecutor(CommandExecutor):
    def is_available(self) -> bool:
        return sys.platform == 'win32'

    def execute(self, payload: CommandPayload) -> CommandResult:
        # Lazy imports to prevent Linux import-time crashes
        import pyautogui
        try:
            from pycaw.utils import AudioUtilities, IAudioEndpointVolume
            from comtypes import CLSCTX_ALL
            audio_available = True
        except ImportError:
            try:
                from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
                from comtypes import CLSCTX_ALL
                audio_available = True
            except ImportError:
                audio_available = False

        level = payload.level
        mute = payload.mute
        
        try:
            if audio_available:
                devices = AudioUtilities.GetSpeakers()
                if hasattr(devices, 'EndpointVolume'):
                    volume = devices.EndpointVolume
                else:
                    interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
                    volume = interface.QueryInterface(IAudioEndpointVolume)
                
                if mute is not None:
                    volume.SetMute(mute, None)
                if level is not None:
                    scalar = max(0.0, min(1.0, level / 100.0))
                    volume.SetMasterVolumeLevelScalar(scalar, None)
                return CommandResult(
                    status=CommandStatus.SUCCESS, 
                    output=f"Volume set to {level}% (Mute: {mute})"
                )
            else:
                raise ImportError("Audio library not found")
        except Exception as e:
            logger.warning(f"Pycaw error: {e}. Trying fallback...")
            try:
                if mute is not None:
                    pyautogui.press('volumemute')
                    return CommandResult(status=CommandStatus.SUCCESS, output="Toggled Mute (Fallback)")
                return CommandResult(
                    status=CommandStatus.SUCCESS, 
                    output="Volume Level not fully supported in fallback mode"
                )
            except Exception as fe:
                return CommandResult(status=CommandStatus.FAILED, output=f"Audio control failed: {e}")

@ExecutorRegistry.register(CommandType.CMD_MEDIA)
class MediaExecutor(CommandExecutor):
    def is_available(self) -> bool:
        return sys.platform == 'win32'

    def execute(self, payload: CommandPayload) -> CommandResult:
        import pyautogui
        action = payload.action
        if action == 'play_pause':
            pyautogui.press('playpause')
        elif action == 'next':
            pyautogui.press('nexttrack')
        elif action == 'prev':
            pyautogui.press('prevtrack')
        
        return CommandResult(status=CommandStatus.SUCCESS, output=f"Media Action: {action}")
