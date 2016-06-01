import re, sys, os

# Mininet imports
from mininet.log import lg, info, error, debug, output
from mininet.util import quietRun
from mininet.node import Host, OVSSwitch, RemoteController
from mininet.cli import CLI
from mininet.net import Mininet
from mininet.topo import SingleSwitchTopo
from subprocess import Popen

def start(ip="127.0.0.1",port=6633):

  ctrlr = lambda n: RemoteController(n, ip=ip, port=port, inNamespace=False)
  net = Mininet(switch=OVSSwitch, controller=ctrlr, autoStaticArp=False)
  c1 = net.addController('c1')

  topo = SingleSwitchTopo(2)
  net.buildFromTopo( topo )

  # Set up logging etc.
  lg.setLogLevel('info')
  lg.setLogLevel('output')

  # Start the network
  net.start()

  # Fork off Frenetic process
  frenetic_proc = Popen(['/home/vagrant/src/frenetic/frenetic.native', 'http-controller'])

  # And fork off application
  app_proc = Popen(['/usr/bin/python2.7/python','/home/vagrant/manual/programmers_guide/code/quick_start/repeater.py'])

  output("Pingall returned "+str(net.pingAll()))

  frenetic_proc.kill()
  app_proc.kill()

os.system("sudo mn -c")
start()