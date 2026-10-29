import siggen
from instruments import hp_8662a


class HP8663A:
    name = "hp8663a"
    pretty_name = "HP 8663A"
    default_resource = "TCPIP::e5810a::gpib0,25::INSTR"

    def __init__(self, _resource_manager, resource_name):
        # The driver speaks VXI-11 itself rather than through pyvisa.
        self.driver = hp_8662a.HP8663A(resource_name)
        self.output_on = False

    def open(self):
        self.driver.open()

    def close(self):
        self.driver.close()

    def set_power(self, power_dBm):
        self.driver.set_power(power_dBm)
        # The driver only sends the level when the output is turned on.
        if self.output_on:
            self.driver.set_output(True)

    def set_output(self, on):
        self.driver.set_output(on)
        self.output_on = on


siggen.SIGGEN_REGISTRY.register(HP8663A)
