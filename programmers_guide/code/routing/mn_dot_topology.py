import re
import sys
from networkx import *
import pygraphviz as pgv

# Mininet imports
from mininet.log import lg, info, error, debug, output
from mininet.util import quietRun
from mininet.node import Host, OVSSwitch, RemoteController
from mininet.cli import CLI
from mininet.net import Mininet

def int_from_mac_colon_hex(mch):
  return int(mch.replace(":",""), 16);

def start(ip="127.0.0.1",port=6633):

  ctrlr = lambda n: RemoteController(n, ip=ip, port=port, inNamespace=False)
  net = Mininet(switch=OVSSwitch, controller=ctrlr, autoStaticArp=False)
  c1 = net.addController('c1')

  topo_agraph = pgv.AGraph("topology.dot")
  for node in topo_agraph.nodes():
    if node.startswith("s"):
      net.addSwitch(node, dpid=str(node.attr['dpid']))
    else:
      # TODO: Need better way to do this
      gw = "10.0.2.1" if node.attr['ip'].startswith("10.0.2") else "10.0.1.1"
      net.addHost( \
        node, 
        mac=node.attr['mac'], 
        ip=node.attr['ip'], 
        defaultRoute="dev "+node+"-eth0 via "+gw
      )

  for link in topo_agraph.edges():
    (src_node, dst_node) = link
    net.addLink(src_node, dst_node, \
      int(link.attr['src_port']), 
      int(link.attr['dport']) 
    )

  # Set up logging etc.
  lg.setLogLevel('info')
  lg.setLogLevel('output')

  # Start the network
  net.start()

  # Enter CLI mode
  output("Network ready\n")
  output("Press Ctrl-d or type exit to quit\n")
  CLI(net)

start()