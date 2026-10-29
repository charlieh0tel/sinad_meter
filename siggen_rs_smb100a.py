import math

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

    def set_frequency(self, frequency_Hz):
        self.driver.set_frequency(frequency_Hz)

    def set_fm(self, rate_Hz, deviation_Hz):
        inst = self.driver.inst
        inst.write(":FM:SOUR INT")
        inst.write(f":LFO:FREQ {rate_Hz}")
        inst.write(f":FM:DEV {deviation_Hz}")
        inst.write(":FM:STAT ON")
        # FM is an option, and the deviation limit depends on the
        # carrier, so read the settings back rather than assume they
        # took.
        for query, expected in (
            (":LFO:FREQ?", rate_Hz),
            (":FM:DEV?", deviation_Hz),
            (":FM:STAT?", 1),
        ):
            actual = float(inst.query(query))
            if not math.isclose(actual, expected, rel_tol=1e-6):
                raise RuntimeError(
                    f"{self.pretty_name}: {query} returned {actual}, "
                    f"expected {expected}"
                )

    def set_power(self, power_dBm):
        self.driver.set_power(power_dBm)

    def set_output(self, on):
        self.driver.set_output(on)


siggen.SIGGEN_REGISTRY.register(RhodeSchwarzSMB100A)
