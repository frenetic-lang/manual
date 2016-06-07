import sys, logging
import frenetic
from frenetic.syntax import *

class RepeaterApp4(frenetic.App):

  client_id = "repeater"

  def port_policy(self, in_port, all_ports):
    return \
      Filter(PortEq(in_port)) >> \
      SetPort( [p for p in all_ports if p != in_port] )

  def all_ports_policy(self, all_ports):
    return Union( self.port_policy(p, all_ports) for p in all_ports )

  def policy(self, switches):
    # We take advantage of the fact there's only one switch
    dpid = switches.keys()[0]
    return self.all_ports_policy(switches[dpid])

  def connected(self):
    def handle_current_switches(switches):
      logging.info("Connected to Frenetic - Switches: "+str(switches))
      self.update(self.policy(switches))
    self.current_switches(callback=handle_current_switches)

logging.basicConfig(stream = sys.stderr, \
  format='%(asctime)s [%(levelname)s] %(message)s', level=logging.INFO \
)

app = RepeaterApp4()
app.start_event_loop()
