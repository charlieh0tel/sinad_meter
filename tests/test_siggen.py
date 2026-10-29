import argparse

import pytest

import auto_sinad
import siggen
import siggen_hp8663a
import siggen_rs_smb100a


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


class FakeSCPI:
    def __init__(self, overrides=None):
        self.settings = {}
        self.overrides = overrides or {}

    def write(self, command):
        (header, value) = command.split(" ")
        self.settings[header] = value

    def query(self, query):
        header = query.rstrip("?")
        if header in self.overrides:
            return self.overrides[header]
        return {"ON": "1"}.get(self.settings[header], self.settings[header])


def make_rs_smb100a(inst):
    gen = siggen_rs_smb100a.RhodeSchwarzSMB100A(None, "unused")
    gen.driver.inst = inst
    return gen


def test_rs_smb100a_sets_internal_fm():
    inst = FakeSCPI()
    make_rs_smb100a(inst).set_fm(1000.0, 3000.0)
    assert inst.settings == {
        ":FM:SOUR": "INT",
        ":LFO:FREQ": "1000.0",
        ":FM:DEV": "3000.0",
        ":FM:STAT": "ON",
    }


def test_rs_smb100a_refuses_fm_it_did_not_take():
    # As when the deviation exceeds what the carrier allows.
    inst = FakeSCPI(overrides={":FM:DEV": "2000.0"})
    with pytest.raises(RuntimeError, match="FM:DEV"):
        make_rs_smb100a(inst).set_fm(1000.0, 3000.0)


def test_hp8663a_refuses_fm():
    with pytest.raises(NotImplementedError):
        siggen_hp8663a.HP8663A(None, "unused").set_fm(1000.0, 3000.0)


def fm_args(**kwargs):
    defaults = {
        "modulation_from_front_panel": False,
        "mod_rate": None,
        "deviation": None,
    }
    return argparse.Namespace(**(defaults | kwargs))


def test_fm_settings_default_to_the_tia_test_modulation():
    assert auto_sinad._fm_settings(fm_args()) == (1000.0, 3000.0)


def test_fm_settings_from_front_panel_are_none():
    assert auto_sinad._fm_settings(fm_args(modulation_from_front_panel=True)) == (
        None,
        None,
    )


def test_fm_settings_reject_deviation_with_front_panel():
    with pytest.raises(ValueError):
        auto_sinad._fm_settings(
            fm_args(modulation_from_front_panel=True, deviation=1500.0)
        )
