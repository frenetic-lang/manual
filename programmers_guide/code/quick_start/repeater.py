import frenetic
from frenetic.syntax import *

class RepeaterApp(frenetic.App):

  client_id = "quick_start"

  def connected(self):
    self.update( id >> SendToController("repeater_app") )

  def packet_in(self, dpid, port_id, payload):
    out_port_id = 2 if port_id == 1 else 1
    self.pkt_out(dpid, payload, SetPort(out_port_id), port_id )

app = RepeaterApp()
app.start_event_loop()
