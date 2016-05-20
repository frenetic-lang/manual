import binascii
import frenetic
from frenetic.syntax import *
from ryu.lib.packet import packet, ether_types, ethernet, arp
from ryu.ofproto import ether
from network_information_base import *

class WaitingPacket(object):
  def __init__(self, dpid, port_id, payload):
    self.dpid = dpid
    self.port_id = port_id
    self.payload = payload

class RouterHandler(object):

  # A list of outstanding ARP requests and packets waiting for the reply
  # { "10.0.1.2" => [WaitingPacket(), WaitingPacket(), ...] }
  arp_requests = {}

  def __init__(self, nib, logger, main_app):
    self.nib = nib
    self.logger = logger
    self.main_app = main_app

  def policy_for_learned_ip(self, cd):
    sn = self.nib.subnet_for(cd.ip)
    return Filter( EthTypeEq(0x800) & IP4DstEq(cd.ip) ) >> \
      SetEthSrc(sn.router_mac) >> SetEthDst(cd.mac) >> \
      SetPort(sn.router_port)

  def policies_for_learned_ips(self):
    return Union(
      self.policy_for_learned_ip(cd) 
      for cd in self.nib.all_learned_macs_with_ip() 
    )

  def learned_dst_ips(self, all_learned_ips):
    return Or( IP4DstEq(ip) for ip in all_learned_ips )

  def policy_for_router(self):
    all_learned_ips = self.nib.all_learned_ips()
    return IfThenElse( 
      EthTypeEq(0x800) & ~ self.learned_dst_ips( all_learned_ips ), 
      SendToController("router"),
      self.policies_for_learned_ips()
    )

  def policy_for_arp(self):
    return Filter(EthTypeEq(0x806)) >> SendToController("router")

  def policy(self):
    return Filter( SwitchEq(self.nib.router_dpid)) >> \
      Union( [ self.policy_for_router(), self.policy_for_arp() ])

  def enqueue_waiting_packet(self, dst_ip, dpid, port_id, payload):
    self.logger.info("Packet for unknown IP "+dst_ip+" received.  Enqueuing packet.")
    if dst_ip not in self.arp_requests:
      sn = self.nib.subnet_for(dst_ip)
      if sn == None:
        self.logger.info("ARP request for "+dst_ip+" has no connected subnet ")
        return

      self.logger.info("Sending ARP Request for "+dst_ip)
      self.arp_request(self.nib.router_dpid, sn.router_port, sn.router_mac, sn.gateway, dst_ip)
      self.arp_requests[dst_ip] = []

    self.arp_requests[dst_ip].append( WaitingPacket(dpid, port_id, payload) )

  def release_waiting_packets(self, dst_ip):
    if dst_ip not in self.arp_requests:
      self.logger.info("ARP reply from "+dst_ip+" released no waiting packets ")
      return

    sn = self.nib.subnet_for(dst_ip)
    if sn == None:
      self.logger.info("ARP reply from "+dst_ip+" has no connected subnet ")
      return

    dst_mac = self.nib.mac_for_ip(dst_ip)
    if dst_mac == None:
      self.logger.info("ARP reply from "+dst_ip+" has no MAC address ")
      return

    for wp in self.arp_requests[dst_ip]:
      actions = [ 
        SetEthSrc(sn.router_mac),
        SetEthDst(dst_mac),
        Output(Physical(sn.router_port))
      ]
      self.main_app.pkt_out(wp.dpid, wp.payload, actions)

    self.logger.info("All packets for IP "+dst_ip+" released.")
    del self.arp_requests[dst_ip]

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

  def arp_request(self, dpid, port, src_mac, src_ip, target_ip):
    e = ethernet.ethernet(dst="ff:ff:ff:ff:ff:ff", src=src_mac, ethertype=ether.ETH_TYPE_ARP)
    pkt = arp.arp_ip(arp.ARP_REQUEST, src_mac, src_ip, "00:00:00:00:00:00", target_ip)
    payload = self.arp_payload(e, pkt)
    self.main_app.pkt_out(dpid, payload, [Output(Physical(port))])

  def packet_in(self, dpid, port_id, payload):
    nib = self.nib

    # If we haven't learned the ports yet, just exit prematurely
    if nib.switch_not_yet_connected():
      return

    # If this packet was not received at the router, just ignore
    if dpid != self.nib.router_dpid:
      return

    # Parse the interesting stuff from the packet
    ethernet_packet = self.main_app.packet(payload, "ethernet")
    src_mac = ethernet_packet.src
    dst_mac = ethernet_packet.dst

    if ethernet_packet.ethertype == ether_types.ETH_TYPE_ARP:
      arp_packet = self.main_app.packet(payload, "arp")
      reply_sent = False
      if arp_packet.opcode == arp.ARP_REQUEST:
        self.logger.info("Got ARP request from "+arp_packet.src_ip+" for "+arp_packet.dst_ip)
        for sn in self.nib.subnets:
          if arp_packet.dst_ip == sn.gateway:
            self.logger.info("ARP Reply sent")
            self.arp_reply( dpid, port_id, src_mac, arp_packet.src_ip, sn.router_mac, arp_packet.dst_ip)
            reply_sent = True
        if not reply_sent:
          self.logger.info("ARP Request Ignored")

      # For ARP replies, see if the reply was meant for us, and release any queued packets if so
      elif arp_packet.src_ip in self.arp_requests:
        src_ip = arp_packet.src_ip
        self.logger.info("ARP reply for "+src_ip+" received.  Releasing packets.")
        dev = nib.hosts[src_mac]
        if src_ip != dev.ip:
          nib.learn( src_mac, dev.dpid, dev.port_id, src_ip )
        self.release_waiting_packets(src_ip)

      else:
        self.logger.info("ARP reply from "+arp_packet.src_ip+" for "+arp_packet.dst_ip+" ignored.")

    elif ethernet_packet.ethertype == ether_types.ETH_TYPE_IP:
      ip_packet = self.main_app.packet(payload,"ipv4")
      src_ip = ip_packet.src
      dst_ip = ip_packet.dst

      # Now send it out the appropriate interface, if we know it.
      dst_mac = nib.mac_for_ip(dst_ip)
      if dst_mac == None:
        # We don't know the mac address, so we send an ARP request and enqueue the packet
        self.enqueue_waiting_packet(dst_ip, dpid, port_id, payload)

      # This will be fairly rare, in the case where we know the destination IP but the rule
      # hasn't been installed yet.  In this case, we emulate what the rule should do.
      else:
        sn = nib.subnet_for(dst_ip)
        if sn != None:
          actions = [ 
            SetEthSrc(sn.router_mac),
            SetEthDst(dst_mac),
            Output(Physical(sn.router_port))
          ]
          self.main_app.pkt_out(dpid, payload, actions)
        else:
          # Usually we would send the packet to the default gateway, but in this case.  
          self.logger.info("Packet for destination "+dst_ip+" on unknown network dropped")
    else:
      self.logger.info("Router: Got packet with Ether type "+str(ethernet_packet.ethertype))
