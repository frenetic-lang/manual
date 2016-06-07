import sys,logging
import frenetic
from frenetic.syntax import *
from frenetic.packet import *
from network_information_base import *

class LearningApp3(frenetic.App):

  client_id = "l2_learning"

  def __init__(self):
    frenetic.App.__init__(self)     
    self.nib = NetworkInformationBase(logging)

  def connected(self):
    def handle_current_switches(switches):
      logging.info("Connected to Frenetic - Switches: "+str(switches))
      dpid = switches.keys()[0]
      self.nib.set_ports( switches[dpid] )
      self.update( id >> SendToController("learning_app") )
    self.current_switches(callback=handle_current_switches)

  def policy_for_dest(self, mac_port):
    (mac, port) = mac_port
    return Filter(EthDstEq(mac)) >> SetPort(port)

  def policies_for_dest(self, all_mac_ports):
    return [ self.policy_for_dest(mp) for mp in all_mac_ports ]

  def policy(self):
    return \
      IfThenElse(
        EthSrcNotEq( self.nib.all_learned_macs() ) | 
          EthDstNotEq( self.nib.all_learned_macs() ),
        SendToController("learning_app"),
        Union( self.policies_for_dest(self.nib.all_mac_port_pairs()) )
      )

  def packet_in(self, dpid, port_id, payload):
    nib = self.nib

    pkt = Packet.from_payload(dpid, port_id, payload)
    src_mac = pkt.ethSrc
    dst_mac = pkt.ethDst

    # If we haven't learned the source mac, do so
    if nib.port_for_mac( src_mac ) == None:
      nib.learn( src_mac, port_id)
      self.update(self.policy())

    # Look up the destination mac and output it through the
    # learned port, or flood if we haven't seen it yet.
    dst_port = nib.port_for_mac( dst_mac )
    if  dst_port != None:
      actions = SetPort(dst_port)
    else:
      actions = SetPort( nib.all_ports_except(port_id) )
    self.pkt_out(dpid, payload, actions )

if __name__ == '__main__':
  logging.basicConfig(\
    stream = sys.stderr, \
    format='%(asctime)s [%(levelname)s] %(message)s', level=logging.INFO \
  )
  app = LearningApp3()
  app.start_event_loop()  
