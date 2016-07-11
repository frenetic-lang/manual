import sys, logging
import frenetic
from frenetic.syntax import *
from network_information_base import *
from tornado.ioloop import PeriodicCallback, IOLoop
from functools import partial

class StatsApp2(frenetic.App):

  client_id = "stats"

  def __init__(self):
    frenetic.App.__init__(self)  

  def repeater_policy(self):
    return Filter(PortEq(1)) >> SetPort(2) | Filter(PortEq(2)) >> SetPort(1) 

  def http_predicate(self):
    return PortEq(1) & EthTypeEq(0x800) & IPProtoEq(6) & TCPDstPortEq(80)

  def policy(self):
    return IfThenElse(
      self.http_predicate(), 
      SendToQuery("http") | SetPort(2), 
      self.repeater_policy()
    )

  def connected(self):
    def handle_current_switches(switches):
      logging.info("Connected to Frenetic - Switches: "+str(switches))
      self.update( self.policy() )
      PeriodicCallback(self.query_http, 5000).start()
    self.current_switches(callback=handle_current_switches)

  def print_count(self, future):
    data = future.result()
    logging.info("Count: {packets = %s, bytes = %s}" % \
      (data[0], data[1]) \
    )

  def query_http(self):
    ftr = self.query("http")
    IOLoop.instance().add_future(ftr, self.print_count)

if __name__ == '__main__':
  logging.basicConfig(\
    stream = sys.stderr, \
    format='%(asctime)s [%(levelname)s] %(message)s', level=logging.INFO \
  )
  app = StatsApp2()
  app.start_event_loop()  
