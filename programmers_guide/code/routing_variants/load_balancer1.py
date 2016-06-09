from frenetic.packet import *
import sys,logging,datetime,time
sys.path.append("../routing")
from load_balancer_nib import *
from switch_handler import *
from load_balancer_handler import *
from tornado.ioloop import IOLoop

class LoadBalancerApp(frenetic.App):

  client_id = "load_balancer"

  def __init__(self, 
    topo_file="../routing/topology.dot", 
    routing_table_file="../routing/routing_table.json",
    load_balancer_file="load_balancer.json"
    ):
    frenetic.App.__init__(self)     
    self.nib = LoadBalancerNIB(
      logging, 
      topo_file, routing_table_file, load_balancer_file
    )

    self.switch_handler = SwitchHandler(self.nib, logging, self)
    self.load_balancer_handler = LoadBalancerHandler(self.nib, logging, self)

  def policy(self):
    return self.switch_handler.policy() | self.load_balancer_handler.policy()

  def update_and_clear_dirty(self):
    self.update(self.policy())
    self.nib.clear_dirty()

  def connected(self):
    def handle_current_switches(switches):
      logging.info("Connected to Frenetic - Switches: "+str(switches))
      self.nib.set_all_ports( switches )
      self.update( self.policy() )
      # Wait a few seconds for the policy to be installed
      logging.info("Pausing 2 seconds to allow rules to be installed")
      IOLoop.instance().add_timeout(datetime.timedelta(seconds=2), 
        self.load_balancer_handler.connected
      )
    self.current_switches(callback=handle_current_switches)

  def packet_in(self, dpid, port, payload):
    pkt = Packet.from_payload(dpid, port, payload)
    self.switch_handler.packet_in(pkt, payload)
    self.load_balancer_handler.packet_in(pkt, payload)

    if self.nib.is_dirty():
      # This doesn't actually wait two seconds, but it serializes the updates 
      # so they occur in the right order
      IOLoop.instance().add_timeout(datetime.timedelta(seconds=2), 
        self.update_and_clear_dirty
      )

  def port_down(self, dpid, port_id):
    self.nib.unlearn( self.nib.mac_for_port_on_switch(dpid, port_id) )
    self.nib.delete_port(dpid, port_id)
    self.update_and_clear_dirty()

  def port_up(self, dpid, port_id):
    # Just to be safe, in case we have old MACs mapped to this port
    self.nib.unlearn( self.nib.mac_for_port_on_switch(dpid, port_id) )
    self.nib.add_port(dpid, port_id)
    self.update_and_clear_dirty()

if __name__ == '__main__':
  logging.basicConfig(\
    stream = sys.stderr, \
    format='%(asctime)s [%(levelname)s] %(message)s', level=logging.INFO \
  )
  app = LoadBalancerApp()
  app.start_event_loop()