from src.shared.enums import CommandType
from src.shared.schemas import CommandPayload


class TestNewCommandTypes:
    def test_all_new_command_types_exist(self):
        assert CommandType.CMD_LIST_PROCESSES
        assert CommandType.CMD_KILL_PROCESS
        assert CommandType.CMD_CLIPBOARD_GET
        assert CommandType.CMD_CLIPBOARD_SET
        assert CommandType.CMD_FILE_LIST
        assert CommandType.CMD_FILE_READ

    def test_payload_has_pid_field(self):
        p = CommandPayload(pid=1234)
        assert p.pid == 1234

    def test_payload_has_text_field(self):
        p = CommandPayload(text="hello clipboard")
        assert p.text == "hello clipboard"

    def test_payload_has_path_field(self):
        p = CommandPayload(path="C:/Users")
        assert p.path == "C:/Users"
