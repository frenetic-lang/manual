import re, sys, os
from networkx import *
import pygraphviz as pgv
from net_utils import NetUtils

# Mininet imports
from mininet.log import lg, info, error, debug, output
from mininet.util import quietRun
from mininet.node import Host, OVSSwitch, RemoteController
from mininet.cli import CLI
from mininet.net import Mininet

class RouterMininetBuilder(object):
  def __init__(self, topo_dot_file):
    self.topo_dot_file = topo_dot_file

  def build(self, net):
    topo_agraph = pgv.AGraph(self.topo_dot_file)
    for node in topo_agraph.nodes():
      if node.startswith("s"):
        net.addSwitch(node, dpid=str(node.attr['dpid']))
      else:
        net.addHost(
          node, 
          mac=node.attr['mac'], 
          ip=node.attr['ip'], 
          defaultRoute="dev "+node+"-eth0 via "+node.attr['gateway']
        )

    for link in topo_agraph.edges():
      (src_node, dst_node) = link
      net.addLink(src_node, dst_node,
        int(link.attr['src_port']), 
        int(link.attr['dport']) 
      )

def start(ip="127.0.0.1",port=6633):

  ctrlr = lambda n: RemoteController(n, ip=ip, port=port, inNamespace=False)
  net = Mininet(switch=OVSSwitch, controller=ctrlr, autoStaticArp=False)
  c1 = net.addController('c1')

  rmb = RouterMininetBuilder("topology.dot")
  rmb.build(net)

  # Set up logging etc.
  lg.setLogLevel('info')
  lg.setLogLevel('output')

  # Start the network
  net.start()

  # Enter CLI mode
  output("Network ready\n")
  output("Press Ctrl-d or type exit to quit\n")
  CLI(net)

if __name__ == '__main__':
  os.system("sudo mn -c")
  start()