import sys,logging
import frenetic
from frenetic.syntax import *
from frenetic.packet import *
from network_information_base_dynamic import *

class VlanApp2(frenetic.App):

  client_id = "handling_vlans"

  def __init__(self):
    frenetic.App.__init__(self)     
    self.nib = NetworkInformationBaseDynamic(logging)

  def connected(self):
    def handle_current_switches(switches):
      logging.info("Connected to Frenetic - Switches: "+str(switches))
      dpid = switches.keys()[0]
      self.nib.set_ports( switches[dpid] )
      self.update( id >> SendToController("vlan_app") )
    self.current_switches(callback=handle_current_switches)

  def policy_for_dest(self, mac_port):
    (mac, port) = mac_port
    mac_vlan = self.nib.vlan_of_port(port)
    return \
      Filter(VlanEq(mac_vlan)) >> \
      Filter(EthDstEq(mac)) >> \
      SetPort(port)

  def policies_for_dest(self, all_mac_ports):
    return [ self.policy_for_dest(mp) for mp in all_mac_ports ]

  def policy(self):
    return \
      IfThenElse(
        EthDstNotEq( self.nib.all_learned_macs() ),
        SendToController("vlan_app"),
        Union( self.policies_for_dest(self.nib.all_mac_port_pairs()) )
      )

  def packet_in(self, dpid, port_id, payload):
    nib = self.nib

    # If we haven't learned the ports yet, just exit prematurely
    if nib.switch_not_yet_connected():
      return

    pkt = Packet.from_payload(dpid, port_id, payload)
    src_mac = pkt.ethSrc
    dst_mac = pkt.ethDst
    src_vlan = pkt.vlan

    # If we haven't learned the source mac, do so
    if nib.port_for_mac( src_mac ) == None:
      nib.learn( src_mac, port_id, src_vlan )
      self.update(self.policy())

    # Look up the destination mac and output it through the
    # learned port, or flood if we haven't seen it yet.
    dst_port = nib.port_for_mac( dst_mac )
    if  dst_port != None:
      # Don't output it if it's on a different VLAN
      dst_vlan = nib.vlan_of_port(dst_port)
      if src_vlan == dst_vlan:
        actions = SetPort(dst_port)
      else:
        actions = [ ]
    else:
      actions = SetPort( nib.all_vlan_ports_except(src_vlan, port_id) )
    self.pkt_out(dpid, payload, actions )

  def port_down(self, dpid, port_id):
    self.nib.unlearn( self.nib.mac_for_port(port_id) )
    self.nib.delete_port(port_id)
    self.update(self.policy())

  def port_up(self, dpid, port_id):
    # Just to be safe, in case we have old MACs mapped to this port
    self.nib.unlearn( self.nib.mac_for_port(port_id) )
    self.nib.add_port(port_id)
    self.update(self.policy())

if __name__ == '__main__':
  logging.basicConfig(\
    stream = sys.stderr, \
    format='%(asctime)s [%(levelname)s] %(message)s', level=logging.INFO \
  )
  app = VlanApp2()
  app.start_event_loop()  
