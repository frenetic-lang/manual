import sys, logging
import frenetic
from frenetic.syntax import *

class RepeaterApp5(frenetic.App):

  client_id = "repeater"

  def port_policy(self, in_port, all_ports):
    return \
      Filter(PortEq(in_port)) >> \
      SetPort( [p for p in all_ports if p != in_port] )

  def all_ports_policy(self, all_ports):
    return Union( self.port_policy(p, all_ports) for p in all_ports )

  def known_ports_pred(self, all_ports):
    return PortEq(all_ports)

  def policy(self):
    return IfThenElse( \
      self.known_ports_pred(self.all_ports), \
      self.all_ports_policy(self.all_ports), \
      SendToController("repeater_app") \
    )

  def connected(self):
    def handle_current_switches(switches):
      logging.info("Connected to Frenetic - Switches: "+str(switches))
      # We take advantage of the fact there's only one switch
      dpid = switches.keys()[0]
      self.all_ports = switches[dpid]
      self.update(self.policy())
    self.current_switches(callback=handle_current_switches)

  def packet_in(self, dpid, port_id, payload):
    if port_id not in self.all_ports:
      self.all_ports.append(port_id)
      self.update(self.policy())
    flood_actions = SetPort( [p for p in self.all_ports if p != port_id] )
    self.pkt_out(dpid, payload, flood_actions )

logging.basicConfig(\
  stream = sys.stderr, \
  format='%(asctime)s [%(levelname)s] %(message)s', level=logging.INFO \
)
app = RepeaterApp5()
app.start_event_loop()  
