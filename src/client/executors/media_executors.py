import logging
from src.client.core.executor import CommandExecutor
from src.client.core.registry import ExecutorRegistry
from src.shared.schemas import CommandPayload, CommandResult
from src.shared.enums import CommandType, CommandStatus

# Imports for Audio/Media
try:
    from pycaw.utils import AudioUtilities, IAudioEndpointVolume
    from comtypes import CLSCTX_ALL
    AUDIO_AVAILABLE = True
except ImportError:
    try:
        from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
        from comtypes import CLSCTX_ALL
        AUDIO_AVAILABLE = True
    except ImportError:
        AUDIO_AVAILABLE = False

try:
    import pyautogui
    PYGUI_AVAILABLE = True
except ImportError:
    PYGUI_AVAILABLE = False

logger = logging.getLogger(__name__)

@ExecutorRegistry.register(CommandType.CMD_SET_VOLUME)
class VolumeExecutor(CommandExecutor):
    def is_available(self) -> bool:
        return AUDIO_AVAILABLE or PYGUI_AVAILABLE

    def execute(self, payload: CommandPayload) -> CommandResult:
        level = payload.level
        mute = payload.mute
        
        try:
            if AUDIO_AVAILABLE:
                devices = AudioUtilities.GetSpeakers()
                # Compat fix
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
            if PYGUI_AVAILABLE:
                if mute:
                    pyautogui.press('volumemute')
                    return CommandResult(status=CommandStatus.SUCCESS, output="Toggled Mute (Fallback)")
                # Fallback for volume level is limited
                return CommandResult(
                    status=CommandStatus.SUCCESS, 
                    output="Volume Level not fully supported in fallback mode"
                )
            return CommandResult(status=CommandStatus.FAILED, output=f"Audio control failed: {e}")

@ExecutorRegistry.register(CommandType.CMD_MEDIA)
class MediaExecutor(CommandExecutor):
    def is_available(self) -> bool:
        return PYGUI_AVAILABLE

    def execute(self, payload: CommandPayload) -> CommandResult:
        if not PYGUI_AVAILABLE:
            return CommandResult(status=CommandStatus.FAILED, output="PyAutoGUI not installed")
        
        action = payload.action
        if action == 'play_pause':
            pyautogui.press('playpause')
        elif action == 'next':
            pyautogui.press('nexttrack')
        elif action == 'prev':
            pyautogui.press('prevtrack')
        
        return CommandResult(status=CommandStatus.SUCCESS, output=f"Media Action: {action}")
