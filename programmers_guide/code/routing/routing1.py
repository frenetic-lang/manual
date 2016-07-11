import sys,logging,datetime
from network_information_base import *
from frenetic import *
from frenetic.packet import *
from switch_handler import *
from router_handler import *
from tornado.ioloop import IOLoop

class RoutingApp(frenetic.App):

  client_id = "routing"

  # TODO: Make this read from same dir as Python file
  def __init__(self, 
    routing_table_file="/home/vagrant/manual/programmers_guide/code/routing/routing_table.json",
    topo_file="/home/vagrant/manual/programmers_guide/code/routing/topology.dot"
    ):
    frenetic.App.__init__(self)     
    self.nib = NetworkInformationBase(logging, topo_file, routing_table_file)

    self.switch_handler = SwitchHandler(self.nib, logging, self)
    self.router_handler = RouterHandler(self.nib, logging, self)

  def policy(self):
    return Union([
      self.switch_handler.policy(),
      self.router_handler.policy(),
    ])

  def update_and_clear_dirty(self):
    self.update(self.policy())
    self.nib.clear_dirty()

  def connected(self):
    def handle_current_switches(switches):
      logging.info("Connected to Frenetic - Switches: "+str(switches))
      self.nib.set_all_ports( switches )
      self.update( self.policy() )
    self.current_switches(callback=handle_current_switches)

  def packet_in(self, dpid, port, payload):
    pkt = Packet.from_payload(dpid, port, payload)
    self.switch_handler.packet_in(pkt, payload)
    self.router_handler.packet_in(pkt, payload)

    if self.nib.is_dirty():
      logging.info("Installing new policy")
      # This doesn't actually wait two seconds, but it serializes the updates 
      # so they occur in the right order
      IOLoop.instance().add_timeout(datetime.timedelta(seconds=2), self.update_and_clear_dirty)

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
  app = RoutingApp()
  app.start_event_loop()