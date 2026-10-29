import siggen
from instruments import rs_smb100a


class RhodeSchwarzSMB100A:
    name = "rssmb100a"
    pretty_name = "R&S SMB100A"
    default_resource = "TCPIP::rssmb100a180609.local::INSTR"

    def __init__(self, resource_manager, resource_name):
        self.driver = rs_smb100a.RhodeSchwarzSMB100A(resource_manager, resource_name)

    def open(self):
        self.driver.open()

    def close(self):
        self.driver.close()

    def set_power(self, power_dBm):
        self.driver.set_power(power_dBm)

    def set_output(self, on):
        self.driver.set_output(on)


siggen.SIGGEN_REGISTRY.register(RhodeSchwarzSMB100A)
