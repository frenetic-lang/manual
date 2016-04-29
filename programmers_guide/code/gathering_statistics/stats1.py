import sys, logging
import frenetic
from frenetic.syntax import *
from network_information_base import *
from tornado.ioloop import PeriodicCallback, IOLoop
from functools import partial

class StatsApp1(frenetic.App):

  client_id = "stats"

  def __init__(self):
    frenetic.App.__init__(self)   
    self.nib = NetworkInformationBase(logging)  

  def connected(self):
    def handle_current_switches(switches):
      logging.info("Connected to Frenetic - Switches: "+str(switches))
      dpid = switches.keys()[0]
      self.nib.set_dpid(dpid)
      self.nib.set_ports( switches[dpid] )
      PeriodicCallback(self.count_ports, 5000).start()
    self.current_switches(callback=handle_current_switches)

  def print_count(self, future, switch):
    data = future.result()
    logging.info("Count %s@%s: {rx_bytes = %s, tx_bytes = %s}" % \
      (switch, data['port_no'], data['rx_bytes'], data['tx_bytes']) \
    )

  def count_ports(self):
    switch_id = self.nib.get_dpid()
    for port in self.nib.all_ports():
      ftr = self.port_stats(switch_id, str(port))
      f = partial(self.print_count, switch = switch_id)
      IOLoop.instance().add_future(ftr, f)

if __name__ == '__main__':
  logging.basicConfig(\
    stream = sys.stderr, \
    format='%(asctime)s [%(levelname)s] %(message)s', level=logging.INFO \
  )
  app = StatsApp1()
  app.start_event_loop()  
