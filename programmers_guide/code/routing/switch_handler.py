import frenetic
from frenetic.syntax import *
from frenetic.packet import *
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

  def packet_in(self, pkt, payload):
    nib = self.nib

    # If we haven't learned the ports yet, just exit prematurely
    if nib.switch_not_yet_connected():
      return

    # If this packet was received at the router, just ignore
    if pkt.switch == self.nib.router_dpid:
      return

    src_mac = pkt.ethSrc
    dst_mac = pkt.ethDst

    # If we haven't learned the source mac
    if nib.port_for_mac_on_switch( src_mac, pkt.switch ) == None: 
      # If this is an IP or ARP packet, record the IP address too
      src_ip = None

      # Don't learn the IP-mac for packets coming in from the router port
      # since they will be incorrect.  (Learn the MAC address though)
      if nib.is_internal_port(pkt.switch, pkt.port):
        pass
      elif pkt.ethType == 0x800 or pkt.ethType == 0x806:   # IP or ARP
        src_ip = pkt.ip4Src

      nib.learn( src_mac, pkt.switch, pkt.port, src_ip)

    # Look up the destination mac and output it through the
    # learned port, or flood if we haven't seen it yet.
    dst_port = nib.port_for_mac_on_switch( dst_mac, pkt.switch )
    if  dst_port != None:
      actions = SetPort(dst_port)
    else:
      actions = SetPort(nib.all_ports_except(pkt.switch, pkt.port))
    self.main_app.pkt_out(pkt.switch, payload, actions )


