import frenetic
from frenetic.syntax import *

class RepeaterApp2(frenetic.App):

    client_id = "repeater"

    def connected(self):
        rule_port_one = Filter(PortEq(1)) >> SetPort(2)
        rule_port_two = Filter(PortEq(2)) >> SetPort(1)
        self.update( rule_port_one | rule_port_two )

app = RepeaterApp2()
app.start_event_loop()