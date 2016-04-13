import sys
sys.path.append('/home/vagrant/src/frenetic/lang/python')
import frenetic
from frenetic.syntax import *

class RepeaterApp(frenetic.App):

  client_id = "quick_start"

  def connected(self):
    self.update( id >> SendToController("repeater_app") )

  def packet_in(self, dpid, port_id, payload):
    out_port = 2 if port_id == 1 else 1
    self.pkt_out(dpid, payload, [ Output(Physical(out_port_id)) ] )

app = RepeaterApp()
app.start_event_loop()
