import argparse
from collections.abc import Collection, Iterable
from typing import cast

import pytest
import pyvisa

import auto_sinad
import siggen
import siggen_hp8663a
import siggen_rs_smb100a

# The adapters only use the resource manager when opened, which these
# tests never do.
UNUSED_RESOURCE_MANAGER = cast(pyvisa.ResourceManager, None)


class RecordingSigGen:
    def __init__(self, fail_on: Collection[str] = ()) -> None:
        self.calls: list[tuple[object, ...]] = []
        self.fail_on = fail_on

    def _record(self, *call: object) -> None:
        self.calls.append(call)
        if call[0] in self.fail_on:
            raise RuntimeError(f"{call[0]} failed")

    def open(self) -> None:
        self._record("open")

    def close(self) -> None:
        self._record("close")

    def set_frequency(self, frequency_Hz: float) -> None:
        self._record("set_frequency", frequency_Hz)

    def set_fm(self, rate_Hz: float, deviation_Hz: float) -> None:
        self._record("set_fm", rate_Hz, deviation_Hz)

    def set_power(self, power_dBm: float) -> None:
        self._record("set_power", power_dBm)

    def set_output(self, on: bool) -> None:
        self._record("set_output", on)


def test_opened_turns_output_off_when_the_block_raises() -> None:
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


def test_opened_closes_even_if_turning_output_off_fails() -> None:
    gen = RecordingSigGen(fail_on=("set_output",))
    with pytest.raises(RuntimeError), siggen.opened(gen):
        pass
    assert gen.calls[-1] == ("close",)


class FakeHPDriver:
    def __init__(self) -> None:
        self.sent_levels: list[float | None] = []
        self.power_dBm: float | None = None

    def set_power(self, power_dBm: float) -> None:
        self.power_dBm = power_dBm

    def set_output(self, on: bool) -> None:
        if on:
            self.sent_levels.append(self.power_dBm)


def test_hp8663a_applies_power_while_output_is_on(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    gen = siggen_hp8663a.HP8663A(UNUSED_RESOURCE_MANAGER, "unused")
    driver = FakeHPDriver()
    monkeypatch.setattr(gen, "driver", driver)
    gen.set_power(-120)
    assert driver.sent_levels == []
    gen.set_output(True)
    gen.set_power(-110)
    assert driver.sent_levels == [-120, -110]


class FakeSCPI:
    def __init__(self, overrides: dict[str, str] | None = None) -> None:
        self.settings: dict[str, str] = {}
        self.overrides = overrides or {}

    def write(self, command: str) -> None:
        (header, value) = command.split(" ")
        self.settings[header] = value

    def query(self, query: str) -> str:
        header = query.rstrip("?")
        if header in self.overrides:
            return self.overrides[header]
        return {"ON": "1"}.get(self.settings[header], self.settings[header])


def make_rs_smb100a(inst: FakeSCPI) -> siggen_rs_smb100a.RhodeSchwarzSMB100A:
    gen = siggen_rs_smb100a.RhodeSchwarzSMB100A(UNUSED_RESOURCE_MANAGER, "unused")
    gen.driver.inst = inst
    return gen


def test_rs_smb100a_sets_internal_fm() -> None:
    inst = FakeSCPI()
    make_rs_smb100a(inst).set_fm(1000.0, 3000.0)
    assert inst.settings == {
        ":FM:SOUR": "INT",
        ":LFO:FREQ": "1000.0",
        ":FM:DEV": "3000.0",
        ":FM:STAT": "ON",
    }


def test_rs_smb100a_refuses_fm_it_did_not_take() -> None:
    # As when the deviation exceeds what the carrier allows.
    inst = FakeSCPI(overrides={":FM:DEV": "2000.0"})
    with pytest.raises(ValueError, match="FM:DEV"):
        make_rs_smb100a(inst).set_fm(1000.0, 3000.0)


class FakeHPInst:
    """A VXI-11 instrument answering MS and serial polls as told."""

    def __init__(self, status_bytes: Iterable[int]) -> None:
        self.sent: list[str] = []
        self.status_bytes = list(status_bytes)

    def write_raw(self, data: bytes) -> None:
        self.sent.append(data.decode())

    def read(self) -> str:
        return "00,000,0\r\n"

    def read_stb(self) -> int:
        return self.status_bytes.pop(0)


def make_hp8663a(inst: FakeHPInst) -> siggen_hp8663a.HP8663A:
    gen = siggen_hp8663a.HP8663A(UNUSED_RESOURCE_MANAGER, "unused")
    gen.driver.inst = inst
    return gen


def test_hp8663a_sets_internal_fm() -> None:
    inst = FakeHPInst([0, 0])
    make_hp8663a(inst).set_fm(1000.0, 3000.0)
    assert inst.sent == ["MS\n", "FM3KZMF1000HZ\n", "MS\n"]


def test_hp8663a_refuses_fm_it_rejected() -> None:
    # An entry error left from before is cleared, not blamed on this entry.
    inst = FakeHPInst([2, 2])
    with pytest.raises(ValueError, match="rejected"):
        make_hp8663a(inst).set_fm(1000.0, 30e3)


def fm_args(**kwargs: object) -> argparse.Namespace:
    defaults = {
        "modulation_from_front_panel": False,
        "mod_rate": None,
        "deviation": None,
    }
    return argparse.Namespace(**(defaults | kwargs))


def test_fm_settings_default_to_the_tia_test_modulation() -> None:
    assert auto_sinad._fm_settings(fm_args()) == (1000.0, 3000.0)


def test_fm_settings_from_front_panel_are_none() -> None:
    assert auto_sinad._fm_settings(fm_args(modulation_from_front_panel=True)) == (
        None,
        None,
    )


def test_fm_settings_reject_deviation_with_front_panel() -> None:
    with pytest.raises(ValueError):
        auto_sinad._fm_settings(
            fm_args(modulation_from_front_panel=True, deviation=1500.0)
        )
