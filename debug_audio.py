
import sys
try:
    import pycaw
    print(f"Pycaw file: {pycaw.__file__}")
except ImportError:
    print("Pycaw not found")

try:
    from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
    print("Imported from pycaw.pycaw (Priority)")
except ImportError:
    try:
        from pycaw.utils import AudioUtilities, IAudioEndpointVolume
        print("Imported from pycaw.utils (Fallback)")
    except ImportError as e:
        print(f"Import failed: {e}")
        sys.exit(1)

from comtypes import CLSCTX_ALL

try:
    print("Attempting GetSpeakers...")
    devices = AudioUtilities.GetSpeakers()
    print(f"GetSpeakers returned type: {type(devices)}")
    print(f"GetSpeakers returned dir: {dir(devices)}")
    
    print("Attempting to access EndpointVolume directly...")
    if hasattr(devices, 'EndpointVolume'):
        print("Found EndpointVolume attribute")
        interface = devices.EndpointVolume
        print(f"EndpointVolume type: {type(interface)}")
        
        # Check if it has the volume methods directly
        if hasattr(interface, 'GetMasterVolumeLevelScalar'):
            print(f"Current Volume (Direct): {interface.GetMasterVolumeLevelScalar()}")
        else:
            # Maybe it IS the IAudioEndpointVolume interface?
            print("Trying to cast or use as interface...")
            # If it's the interface, we can use it directly?
            # Or maybe we need to use it to get the scalar?
            try:
                print(f"Volume Scalar: {interface.GetMasterVolumeLevelScalar()}")
            except Exception as e:
                print(f"Direct call failed: {e}")
    else:
        print("No EndpointVolume attribute")
except Exception as e:
    print(f"Error: {e}")
