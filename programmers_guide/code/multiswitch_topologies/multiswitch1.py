import sys,logging
import frenetic
from frenetic.syntax import *
from frenetic.packet import *
from network_information_base import *

class MultiswitchApp1(frenetic.App):

  client_id = "multiswitch"

  def __init__(self):
    frenetic.App.__init__(self)     
    self.nib = NetworkInformationBase(logging)

  def connected(self):
    def handle_current_switches(switches):
      logging.info("Connected to Frenetic - Switches: "+str(switches))
      self.nib.set_all_ports( switches )
      self.update( self.policy() )
    self.current_switches(callback=handle_current_switches)

  def policy_for_dest(self, dpid, mac_port):
    (mac, port) = mac_port
    return Filter(EthDstEq(mac)) >> SetPort(port)

  def policies_for_dest(self, dpid, all_mac_ports):
    return [ self.policy_for_dest(dpid, mp) for mp in all_mac_ports ]

  def policy_for_edge_switch(self, dpid):
    return \
      Filter(SwitchEq(dpid)) >> \
      IfThenElse(
        (EthSrcNotEq( self.nib.all_learned_macs_on_switch(dpid) ) | 
        EthDstNotEq( self.nib.all_learned_macs_on_switch(dpid) )),
        SendToController("multiswitch"),
        Union( self.policies_for_dest(dpid, self.nib.all_mac_port_pairs_on_switch(dpid)) )
      )

  def policy_for_edge_switches(self):
    return Union(self.policy_for_edge_switch(dpid) for dpid in self.nib.edge_switch_dpids())

  def flood_core_switch(self, dpid, port_id):
    outputs = SetPort( self.nib.all_ports_except(dpid, port_id) )
    return Filter(PortEq(port_id)) >> outputs

  def policy_for_core_switch(self):
    dpid = self.nib.core_switch_dpids()[0]
    return Filter(SwitchEq(dpid)) >> \
      Union(self.flood_core_switch(dpid, p) for p in self.nib.ports[dpid])

  def policy(self):
    return self.policy_for_core_switch() | self.policy_for_edge_switches()

  def packet_in(self, dpid, port_id, payload):
    nib = self.nib

    # If we haven't learned the ports yet, just exit prematurely
    if nib.switch_not_yet_connected():
      return

    pkt = Packet.from_payload(dpid, port_id, payload)
    src_mac = pkt.ethSrc
    dst_mac = pkt.ethDst

    # If we haven't learned the source mac, do so
    if nib.port_for_mac_on_switch( src_mac, dpid ) == None: 
      # Don't learn the mac for packets coming in from internal ports
      if nib.is_internal_port(dpid, port_id):
        pass
      else:
        nib.learn( src_mac, dpid, port_id )
        self.update(self.policy())

    # Look up the destination mac and output it through the
    # learned port, or flood if we haven't seen it yet.
    dst_port = nib.port_for_mac_on_switch( dst_mac, dpid )
    if  dst_port != None:
      actions = SetPort(dst_port)
    else:
      actions = SetPort( nib.all_ports_except(dpid, port_id) )
    self.pkt_out(dpid, payload, actions )

  def port_down(self, dpid, port_id):
    self.nib.unlearn( self.nib.mac_for_port_on_switch(dpid,port_id) )
    self.nib.delete_port(dpid, port_id)
    self.update(self.policy())

  def port_up(self, dpid, port_id):
    # Just to be safe, in case we have old MACs mapped to this port
    self.nib.unlearn( self.nib.mac_for_port_on_switch(dpid,port_id) )
    self.nib.add_port(dpid, port_id)
    self.update(self.policy())

if __name__ == '__main__':
  logging.basicConfig(\
    stream = sys.stderr, \
    format='%(asctime)s [%(levelname)s] %(message)s', level=logging.INFO \
  )
  app = MultiswitchApp1()
  app.start_event_loop()  
