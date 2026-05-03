from src.shared.schemas import CommandPayload


class TestCommandPayload:
    def test_accepts_command_str(self):
        p = CommandPayload(command_str="ipconfig /all")
        assert p.command_str == "ipconfig /all"

    def test_command_str_defaults_to_none(self):
        p = CommandPayload()
        assert p.command_str is None
