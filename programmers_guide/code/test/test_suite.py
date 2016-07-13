import re, sys, os, psutil, time
from subprocess import *

# Mininet imports
from mininet.log import lg, info, error, debug, output
from mininet.util import quietRun
from mininet.node import Host, OVSSwitch, RemoteController
from mininet.cli import CLI
from mininet.net import Mininet
from mininet.topo import SingleSwitchTopo
from mininet.topolib import TreeTopo
from mininet.clean import Cleanup

CODE_ROOT = '/home/vagrant/manual/programmers_guide/code/'
VERBOSE = False

def pingall_test(folder, exe, topo=SingleSwitchTopo(4), custom_topo=None, custom_test=None, expect_pct=0):

  ip="127.0.0.1"
  port=6633

  if not VERBOSE:
    lg.setLogLevel('critical')

  ctrlr = lambda n: RemoteController(n, ip=ip, port=port, inNamespace=False)
  net = Mininet(switch=OVSSwitch, controller=ctrlr, autoStaticArp=False,cleanup=True)
  c1 = net.addController('c1')

  if custom_topo:
    custom_topo.build(net)
  else:
    net.buildFromTopo(topo)

  # Start the network
  net.start()

  # Fork off Frenetic process
  devnull = None if VERBOSE else open(os.devnull, 'w')
  frenetic_proc = Popen(
    ['/home/vagrant/src/frenetic/frenetic.native', 'http-controller','--verbosity','debug'],
    stdout=devnull, stderr=devnull
  )

  # Wait a few seconds for frenetic to initialize, otherwise 
  time.sleep(5)

  # And fork off application
  app_proc = Popen(
    ['/usr/bin/python2.7',exe],
    stdout=devnull, stderr=devnull, cwd=CODE_ROOT+folder
  )

  if custom_test:
    got_pct = int(custom_test(net))
  else:
    got_pct = int(net.pingAll())

  expected_msg = " expected "+str(expect_pct)+"% dropped got "+str(got_pct)+"% dropped" 
  print exe + ("...ok" if expect_pct==got_pct else expected_msg)

  frenetic_proc.kill()
  app_proc.kill()

  # Ocassionally shutting down the network throws an error, which is superfluous because
  # the net is already shut down.  So ignore.  
  try:
    net.stop()
  except OSError:
    pass

def load_balancer_test(net):
  time.sleep(5)  # Wait for rules to be propogated
  successful_pings = 0
  # Pings wait for 60 seconds because the first one generates a lot of ARPs which 
  # are slow to get answered.  
  ping_front1 = net.getNodeByName("h1").cmd("ping -c 1 -w 60 10.0.2.100")
  if re.search('1 received',ping_front1):
    successful_pings += 1
  ping_front2 = net.getNodeByName("h2").cmd("ping -c 1 -w 60 10.0.2.100")
  if re.search('1 received',ping_front2):
    successful_pings += 1
  return ((2 - successful_pings) / 2.0) * 100.0

if os.getenv("SUDO_USER") == None: 
  print "This program need 'sudo'"; 
  exit()

# Clean up from the last disaster
Cleanup()
for proc in psutil.process_iter():
  if proc.name() == "frenetic.native" or proc.name() == "openflow.native":
    proc.kill()

# Test Suite
pingall_test("quick_start", "repeater.py", topo=SingleSwitchTopo(2))
pingall_test("netkat_principles", "repeater2.py", topo=SingleSwitchTopo(2))
pingall_test("netkat_principles", "repeater3.py", expect_pct=100)
pingall_test("netkat_principles", "repeater4.py")
pingall_test("netkat_principles", "repeater5.py")
pingall_test("l2_learning_switch", "learning1.py")
pingall_test("l2_learning_switch", "learning2.py", expect_pct=100)
pingall_test("l2_learning_switch", "learning3.py")
pingall_test("l2_learning_switch", "learning4.py")
pingall_test("handling_vlans", "vlan1.py", expect_pct=66)
sys.path.append("../handling_vlans")
from mn_custom_topo import VlanMininetBuilder
ct = VlanMininetBuilder()
pingall_test("handling_vlans", "vlan2.py", custom_topo=ct, expect_pct=83)
pingall_test("multiswitch_topologies", "multiswitch1.py", topo=TreeTopo(2,4))
pingall_test("multiswitch_topologies", "multiswitch2.py", topo=TreeTopo(2,4))
pingall_test("multiswitch_topologies", "multiswitch3.py", topo=TreeTopo(3,3))
sys.path.append("../routing")
from mn_dot_topology import RouterMininetBuilder
ct = RouterMininetBuilder(CODE_ROOT + "/routing/topology.dot")
pingall_test("routing", "routing1.py", custom_topo=ct)
pingall_test("routing_variants", "load_balancer1.py", custom_topo=ct, custom_test=load_balancer_test)
pingall_test("routing_variants", "load_balancer2.py", custom_topo=ct, custom_test=load_balancer_test)
