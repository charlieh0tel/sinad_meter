import siggen
from instruments import rs_smb100a


class RhodeSchwarzSMB100A:
    api_version = siggen.API_VERSION
    name = "rssmb100a"
    pretty_name = "R&S SMB100A"
    default_resource = "TCPIP::rssmb100a180609.local::INSTR"

    def __init__(self, resource_manager, resource_name):
        self.driver = rs_smb100a.RhodeSchwarzSMB100A(resource_manager, resource_name)

    def open(self):
        self.driver.open()

    def close(self):
        self.driver.close()

    def set_frequency(self, frequency_Hz):
        self.driver.set_frequency(frequency_Hz)

    def set_fm(self, rate_Hz, deviation_Hz):
        self.driver.set_fm(rate_Hz, deviation_Hz)

    def set_power(self, power_dBm):
        self.driver.set_power(power_dBm)

    def set_output(self, on):
        self.driver.set_output(on)


siggen.register(RhodeSchwarzSMB100A)
