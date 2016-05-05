import sys,logging
import frenetic
from frenetic.syntax import *
from ryu.lib.packet import ethernet
from network_information_base import *

class NatApp1(frenetic.App):

  client_id = "nat"

  def __init__(self):
    frenetic.App.__init__(self)     
    self.nib = NetworkInformationBase(logging)

  def connected(self):
    def handle_current_switches(switches):
      logging.info("Connected to Frenetic - Switches: "+str(switches))
      self.nib.connected(switches.keys()[0])
      self.update( id >> SendToController("nat_app") )
    self.current_switches(callback=handle_current_switches)

  def predicate_flow_match(self, f):
    return EthTypeEq(0x800) & IPProtoEq(6) & \
      IP4SrcEq(f.src_ip) & TCPSrcPortEq(f.src_tcp_port) & \
      IP4DstEq(f.dst_ip) & TCPDstPortEq(f.dst_tcp_port)

  def predicate_all_flow_matches(self, all_flows):
    return Or( \
      self.predicate_flow_match(f) for f in self.nib.all_flows() 
    )

  def rewrite_actions(self, f):
    (rewrite_ip, rewrite_tcp_port, _ ) = self.nib.rewrite_for_flow(f)
    (rewrite_port, rewrite_mac) = self.nib.port_and_mac_of_ip(rewrite_ip)
    if f.direction == Flow.OUTGOING:
      return  ( [ \
        SetIP4Src(rewrite_ip), SetTCPSrcPort(rewrite_tcp_port), 
        SetEthSrc(rewrite_mac)
      ], rewrite_port)  
    else:
      return  ([ \
        SetIP4Dst(rewrite_ip), SetTCPDstPort(rewrite_tcp_port), 
        SetEthDst(rewrite_mac)
      ], rewrite_port)

  def rewrite_actions_for_rule(self, f):
    (rewrites, port) = self.rewrite_actions(f)
    rewrites.append( SetPort(port) )
    return rewrites

  def rewrite_actions_for_pkt_out(self, f):
    (rewrites, port) = self.rewrite_actions(f)
    rewrites.append( Output(Physical(port)) )
    return rewrites

  def rewrite_rule(self, f):
    return Filter(self.predicate_flow_match(f)) >> Seq(self.rewrite_actions_for_rule(f))

  def all_rewrite_rules(self):
    return Union( self.rewrite_rule(f) for f in self.nib.all_flows() )

  def policy(self):
    all_flows = self.nib.all_flows()
    return \
      IfThenElse(
        self.predicate_all_flow_matches(all_flows),
        self.all_rewrite_rules(),
        SendToController("nat_app")
      )

  def packet_in(self, dpid, port_id, payload):
    nib = self.nib

    # If we haven't learned the ports yet, just exit prematurely
    if nib.switch_not_yet_connected():
      return

    # Parse the interesting stuff from the packet
    ethernet_packet = self.packet(payload, "ethernet")
    src_mac = ethernet_packet.src
    dst_mac = ethernet_packet.dst

    # If it's not an IP or TCP packet, just drop it
    if ethernet_packet.ethertype == 0x800:
      ip_packet = self.packet(payload, "ipv4")
      if ip_packet.proto == 6:
        tcp_packet = self.packet(payload, "tcp")
        pkt_flow = Flow(ip_packet.src, tcp_packet.src_port, ip_packet.dst, tcp_packet.dst_port, Flow.OUTGOING)
        if nib.learn(port_id, src_mac, pkt_flow):
          self.update(self.policy())

        # Then apply the matching actions
        actions = self.rewrite_actions_for_pkt_out(pkt_flow)
        self.pkt_out(dpid, payload, actions )
      else:
        logging.info("IP Non-TCP Packet Dropped")
    else:
      logging.info("Non-IP Packet Dropped")

if __name__ == '__main__':
  logging.basicConfig(\
    stream = sys.stderr, \
    format='%(asctime)s [%(levelname)s] %(message)s', level=logging.INFO \
  )
  app = NatApp1()
  app.start_event_loop()  
