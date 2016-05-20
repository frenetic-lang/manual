import frenetic
from frenetic.syntax import *
from ryu.lib.packet import ethernet, ether_types, ipv4, arp
from network_information_base import *

class SwitchHandler(object):

  def __init__(self, nib, logger, main_app):
    self.nib = nib
    self.logger = logger
    self.main_app = main_app

  def policy_for_dest(self, dpid, mac_port):
    (mac, port) = mac_port
    return Filter(SwitchEq(dpid) & EthDstEq(mac)) >> SetPort(port)

  def policies_for_dest(self, dpid, all_mac_ports):
    return [ self.policy_for_dest(dpid, mp) for mp in all_mac_ports ]

  def policy_for_switch(self, dpid):
    return \
      IfThenElse(
        SwitchEq(dpid) & 
        (EthSrcNotEq( self.nib.all_learned_macs_on_switch(dpid) ) | 
        EthDstNotEq( self.nib.all_learned_macs_on_switch(dpid) )),
        SendToController("switch"),
        Union( self.policies_for_dest(dpid, self.nib.all_mac_port_pairs_on_switch(dpid)) )
      )

  def policy(self):
    return Union(self.policy_for_switch(dpid) for dpid in self.nib.switch_dpids())

  def packet_in(self, dpid, port_id, payload):
    nib = self.nib

    # If we haven't learned the ports yet, just exit prematurely
    if nib.switch_not_yet_connected():
      return

    # If this packet was received at the router, just ignore
    if dpid == self.nib.router_dpid:
      return

    # Parse the interesting stuff from the packet
    ethernet_packet = self.main_app.packet(payload, "ethernet")
    src_mac = ethernet_packet.src
    dst_mac = ethernet_packet.dst

    # If we haven't learned the source mac
    if nib.port_for_mac_on_switch( src_mac, dpid ) == None: 
      # If this is an IP or ARP packet, record the IP address too
      src_ip = None

      # Don't learn the IP-mac for packets coming in from the router port
      # since they will be incorrect.  (Learn the MAC address though)
      if nib.is_internal_port(dpid, port_id):
        pass
      elif ethernet_packet.ethertype == ether_types.ETH_TYPE_IP:
        src_ip = self.main_app.packet(payload,"ipv4").src
      elif ethernet_packet.ethertype == ether_types.ETH_TYPE_ARP:
        src_ip = self.main_app.packet(payload,"arp").src_ip

      nib.learn( src_mac, dpid, port_id, src_ip)

    # Look up the destination mac and output it through the
    # learned port, or flood if we haven't seen it yet.
    dst_port = nib.port_for_mac_on_switch( dst_mac, dpid )
    if  dst_port != None:
      actions = [ Output(Physical(dst_port)) ]
    else:
      actions = [ Output(Physical(p)) for p in nib.all_ports_except(dpid, port_id) ]
    self.main_app.pkt_out(dpid, payload, actions )


