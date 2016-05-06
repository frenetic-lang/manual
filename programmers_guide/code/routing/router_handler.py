import binascii
import frenetic
from frenetic.syntax import *
from ryu.lib.packet import packet, ethernet, arp
from ryu.ofproto import ether
from network_information_base import *

class RouterHandler():

  client_id = "router"

  def __init__(self, nib, logging, main_app):
    self.nib = nib
    self.logging = logging
    self.main_app = main_app

  def policy_for_learned_mac(self, mac, dpid):
    rp = self.nib.router_port_for_switch(dpid)
    return EthTypeEq(0x800) & IP4DstEq()

  def policies_for_learned_macs(self):
    return Union( \
      self.policy_for_learned_mac(mac, dpid) 
      for (mac, dpid, _) in self.nib.all_learned_macs() 
    )

  def policies_for_subnet(self, subnet, mask, port):
    return Filter ( EthTypeEq(0x800) & IP4DstEq(subnet, mask) ) >> \
      SetEthDst("ff:ff:ff:ff:ff:ff") >> SetPort(port)

  def policies_for_subnets(self):
    return Union( self.policies_for_subnet(subnet,mask,port) for (subnet,mask,port) in self.nib.subnets )

  def policy_for_arp(self):
    return Filter(EthTypeEq(0x806)) >> SendToController("router")

  def policy(self):
    return Filter( SwitchEq(self.nib.router_dpid)) >> \
      Union( [ self.policies_for_subnets(), self.policy_for_arp() ])

  def arp_payload(self, e, pkt):
    p = packet.Packet()
    p.add_protocol(e)
    p.add_protocol(pkt)
    p.serialize()
    return NotBuffered(binascii.a2b_base64(binascii.b2a_base64(p.data)))

  def arp_reply(self, dpid, port, src_mac, src_ip, target_mac, target_ip):
    e = ethernet.ethernet(dst=src_mac, src=target_mac, ethertype=ether.ETH_TYPE_ARP)
    # Note for the reply we flip the src and target, as per ARP rules
    pkt = arp.arp_ip(arp.ARP_REPLY, target_mac, target_ip, src_mac, src_ip)
    payload = self.arp_payload(e, pkt)
    self.main_app.pkt_out(dpid, payload, [Output(Physical(port))])

  def packet_in(self, dpid, port_id, payload):
    nib = self.nib

    # If we haven't learned the ports yet, just exit prematurely
    if nib.switch_not_yet_connected():
      return

    # Parse the interesting stuff from the packet
    ethernet_packet = self.main_app.packet(payload, "ethernet")
    src_mac = ethernet_packet.src
    dst_mac = ethernet_packet.dst

    if ethernet_packet.ethertype == 0x806:
      arp_packet = self.main_app.packet(payload, "arp")
      if arp_packet.opcode == arp.ARP_REQUEST:
        self.logging.info("Got ARP request from "+arp_packet.src_ip+" for "+arp_packet.dst_ip)
        # TODO: Do this by config rules
        if arp_packet.dst_ip.startswith("10.0.1") or arp_packet.dst_ip.startswith("10.0.2"):
          self.arp_reply( dpid, port_id, src_mac, arp_packet.src_ip, self.nib.router_mac, arp_packet.dst_ip)
    else:
      self.logging.info("Router: Got packet with Ether type "+str(ethernet_packet.ethertype))
