import pytest

import siggen
import siggen_hp8663a


class RecordingSigGen:
    def __init__(self, fail_on=()):
        self.calls = []
        self.fail_on = fail_on

    def _record(self, *call):
        self.calls.append(call)
        if call[0] in self.fail_on:
            raise RuntimeError(f"{call[0]} failed")

    def open(self):
        self._record("open")

    def close(self):
        self._record("close")

    def set_output(self, on):
        self._record("set_output", on)


def test_opened_turns_output_off_when_the_block_raises():
    gen = RecordingSigGen()
    with pytest.raises(ValueError), siggen.opened(gen):
        gen.set_output(True)
        raise ValueError
    assert gen.calls == [
        ("open",),
        ("set_output", True),
        ("set_output", False),
        ("close",),
    ]


def test_opened_closes_even_if_turning_output_off_fails():
    gen = RecordingSigGen(fail_on=("set_output",))
    with pytest.raises(RuntimeError), siggen.opened(gen):
        pass
    assert gen.calls[-1] == ("close",)


class FakeHPDriver:
    def __init__(self):
        self.sent_levels = []
        self.power_dBm = None

    def set_power(self, power_dBm):
        self.power_dBm = power_dBm

    def set_output(self, on):
        if on:
            self.sent_levels.append(self.power_dBm)


def test_hp8663a_applies_power_while_output_is_on():
    gen = siggen_hp8663a.HP8663A(None, "unused")
    gen.driver = FakeHPDriver()
    gen.set_power(-120)
    assert gen.driver.sent_levels == []
    gen.set_output(True)
    gen.set_power(-110)
    assert gen.driver.sent_levels == [-120, -110]
