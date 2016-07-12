import re, sys

# Mininet imports
from mininet.log import lg, info, error, debug, output
from mininet.util import quietRun
from mininet.node import Host, OVSSwitch, RemoteController
from mininet.cli import CLI
from mininet.net import Mininet


# Mercilessly copied from https://github.com/mininet/mininet/blob/master/examples/vlanhost.py
#
class VLANHost( Host ):
  "Host connected to VLAN interface"

  def config( self, vlan=100, **params ):
    """Configure VLANHost according to (optional) parameters:
       vlan: VLAN ID for default interface"""

    r = super( VLANHost, self ).config( **params )

    intf = self.defaultIntf()
    # remove IP from default, "physical" interface
    self.cmd( 'ifconfig %s inet 0' % intf )
    # create VLAN interface
    self.cmd( 'vconfig add %s %d' % ( intf, vlan ) )
    # assign the host's IP to the VLAN interface
    self.cmd( 'ifconfig %s.%d inet %s' % ( intf, vlan, params['ip'] ) )
    # update the intf name and host's intf map
    newName = '%s.%d' % ( intf, vlan )
    # update the (Mininet) interface to refer to VLAN interface name
    intf.name = newName
    # add VLAN interface to host's name to intf map
    self.nameToIntf[ newName ] = intf

    return r

class VlanMininetBuilder(object):

  def build(self, net):
    net.addSwitch('s1', dpid = '10:00:00:00:00:00' )

    h1 = net.addHost('h1', cls=VLANHost, mac='00:00:00:00:00:01', 
        ip='10.0.0.1', vlan=1001)
    net.addLink("s1", h1, 1, 0)

    h2 = net.addHost('h2', cls=VLANHost, mac='00:00:00:00:00:02', 
        ip='10.0.0.2', vlan=1002)
    net.addLink("s1", h2, 2, 0)

    h3 = net.addHost('h3', cls=VLANHost, mac='00:00:00:00:00:03', 
        ip='10.0.0.3', vlan=1001)
    net.addLink("s1", h3, 3, 0)

    h4 = net.addHost('h4', cls=VLANHost, mac='00:00:00:00:00:04', 
        ip='10.0.0.4', vlan=1002)
    net.addLink("s1", h4, 4, 0)


def start(ip="127.0.0.1",port=6633):
  ctrlr = lambda n: RemoteController(n, ip=ip, port=port, inNamespace=False)
  net = Mininet(switch=OVSSwitch, controller=ctrlr, autoStaticArp=False)
  c1 = net.addController('c1')

  vmb = VlanMininetBuilder()
  vmb.build(net)

  # Set up logging etc.
  lg.setLogLevel('info')
  lg.setLogLevel('output')

  # Start the network
  net.start()

  # Enter CLI mode
  output("Network ready\n")
  output("Press Ctrl-d or type exit to quit\n")
  CLI(net)
  net.stop()

if __name__ == '__main__':
  os.system("sudo mn -c")
  start()