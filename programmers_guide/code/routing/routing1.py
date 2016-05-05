import sys,logging,datetime
from network_information_base import *
from switch_handler import *
from router_handler import *
from tornado.ioloop import IOLoop


class RoutingApp(frenetic.App):

  client_id = "routing"

  def __init__(self, topo_file="topology.dot"):
    frenetic.App.__init__(self)     
    self.nib = NetworkInformationBase(logging)
    #self.nib.load_topo(topo_file)

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
    self.switch_handler.packet_in(dpid, port, payload)
    self.router_handler.packet_in(dpid, port, payload)

    if self.nib.is_dirty():
      logging.info("Installing new policy")
      # This doesn't actually wait two seconds, but it seems to serialize the updates so they occur in the right
      # order, as opposed to just calling update_and_clear_dirty on its own.
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