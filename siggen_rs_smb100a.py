import pyvisa

import siggen
from instruments import rs_smb100a


class RhodeSchwarzSMB100A:
    api_version = siggen.API_VERSION
    name = "rssmb100a"
    pretty_name = "R&S SMB100A"
    default_resource = "TCPIP::rssmb100a180609.local::INSTR"

    def __init__(
        self, resource_manager: pyvisa.ResourceManager, resource_name: str
    ) -> None:
        self.driver = rs_smb100a.RhodeSchwarzSMB100A(resource_manager, resource_name)

    def open(self) -> None:
        self.driver.open()

    def close(self) -> None:
        self.driver.close()

    def set_frequency(self, frequency_Hz: float) -> None:
        self.driver.set_frequency(frequency_Hz)

    def set_fm(self, rate_Hz: float, deviation_Hz: float) -> None:
        self.driver.set_fm(rate_Hz, deviation_Hz)

    def set_power(self, power_dBm: float) -> None:
        self.driver.set_power(power_dBm)

    def set_output(self, on: bool) -> None:
        self.driver.set_output(on)


siggen.register(RhodeSchwarzSMB100A)
