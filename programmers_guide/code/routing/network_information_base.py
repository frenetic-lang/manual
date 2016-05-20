import json
import pygraphviz as pgv
from net_utils import NetUtils

class ConnectedDevice(object):
  dpid = None
  port_id = None
  ip = None
  mac = None

  def __init__(self, dpid, port_id, ip, mac):
    self.dpid = dpid
    self.port_id = port_id
    self.ip = ip
    self.mac = mac

  def __str__(self):
    return str(self.ip)+"/"+self.mac+ \
      " attached to ( "+str(self.dpid)+" , "+str(self.port_id)+" )"

class Subnet(object):
  dpid = None
  subnet_cidr = None
  router_port = None
  gateway = None

  def __init__(self, subnet_cidr, router_port, router_mac, gateway):
    self.subnet_cidr = subnet_cidr 
    self.router_mac = router_mac
    self.router_port = router_port
    self.gateway = gateway

class NetworkInformationBase(object):

  # hosts is a dictionary of MAC addresses to ConnectedDevice
  #  { "11:11:11:11:11:11": ConnectedDevice() ...}
  hosts = {}

  # dictionary of live ports on each switch
  # { "11:11:11:11:11:11": [1,2], ...}
  ports = {}

  # dictionary of router ports (internal ports) on each switch
  # { "11:11:11:11:11:11": [3], ...}
  internal_ports = {}

  # Dirty flag set if policies need to be regenerated and sent to switches
  dirty = False

  # Router 
  router_dpid = None

  # List of all subnets connected to the router
  subnets = [ ] 

  def __init__(self, logger, topo_file, routing_table_file):
    self.logger = logger

    # Read the Fixed routing table first
    f = open(routing_table_file, "r")
    routing_config = json.load(f)
    f.close()
    for rt in routing_config:
      sn = Subnet(rt["subnet"],rt["router_port"],rt["router_mac"],rt["gateway"])
      self.subnets.append(sn)

    # Read the fixed configuration from the topology file
    topo_agraph = pgv.AGraph(topo_file)
    switchnames = {}

    # Read router name and dpid from topo
    for node in topo_agraph.nodes():
      if node.startswith("s"): 
        if node.attr["router"]:
          router_name = str(node)
          self.router_dpid = NetUtils.int_from_mac_colon_hex(node.attr["dpid"])
        else: 
          switchnames[str(node)] = NetUtils.int_from_mac_colon_hex(node.attr["dpid"])

    # Mark all the internal ports in the switches, since these need special attention
    for link in topo_agraph.edges():
      (src_node, dst_node) = link
      if str(src_node) == router_name:
        dpid = switchnames[ str(dst_node) ]
        if dpid not in self.internal_ports:
          self.internal_ports[dpid] = []
        self.internal_ports[dpid].append(int(link.attr['dport']))

  def is_internal_port(self, dpid, port_id):
    return port_id in self.internal_ports[dpid]

  def subnet_for(self, ip):
    for sn in self.subnets:
      if NetUtils.ip_in_network(ip, sn.subnet_cidr):
        return sn
    return None

  def switch_dpids(self):
    return [dpid for dpid in self.ports.keys() if dpid != self.router_dpid]

  def learn(self, mac, dpid, port_id, ip):
    # Flag it if we've already learned the IP
    if ip != None and self.mac_for_ip(ip) != None:
      self.logger.error(
        "Saw IP " + ip + "on mac "+mac+
        " but it's already assigned to "+self.mac_for_ip(ip)
      )
      return

    # Do not learn a mac twice, but record the IP address if new
    if mac in self.hosts:
      if ip != self.hosts[mac].ip:
        self.hosts[mac].ip = ip
        self.set_dirty()
      return

    cd = ConnectedDevice(dpid, port_id, ip, mac)
    self.hosts[mac] = cd
    self.logger.info( "Learning: "+ str(cd) )
    self.set_dirty()

  def port_for_mac_on_switch(self, mac, dpid):
    return self.hosts[mac].port_id \
      if mac in self.hosts and self.hosts[mac].dpid == dpid else None

  def mac_for_port_on_switch(self, dpid, port_id):
    for mac in self.hosts:
      if self.hosts[mac].dpid == dpid and self.hosts[mac].port_id == port_id:
        return mac
    return None

  def all_learned_macs_with_ip(self):
    return [ cd for (_, cd) in self.hosts.iteritems() if cd.ip != None ]

  def non_gateway(self, ip):
    for sn in self.subnets:
      if sn.gateway == ip:
        return False
    return True

  def all_learned_ips(self):
    return [ 
      cd.ip for (_, cd) in self.hosts.iteritems() 
        if cd.ip != None and self.non_gateway(cd.ip) 
    ]

  def mac_for_ip(self, ip):
    for (_,cd) in self.hosts.iteritems():
      if cd.ip == ip:
        return cd.mac
    return None

  def unlearn(self, mac):
    if mac in self.hosts:
      del self.hosts[mac]
      self.set_dirty()

  def all_mac_port_pairs_on_switch(self, dpid):
    return [ 
      (mac, self.hosts[mac].port_id) 
      for mac in self.hosts.keys() if self.hosts[mac].dpid == dpid 
    ]

  def all_learned_macs_on_switch(self, dpid):
    return [
      mac for mac in self.hosts.keys() if self.hosts[mac].dpid == dpid 
    ]

  def set_all_ports(self, switch_list):
    self.ports = switch_list

  def add_port(self, dpid, port_id):
    if port_id not in self.ports[dpid]:
      self.ports.append(port_id)

  def delete_port(self, dpid, port_id):
    if port_id in self.ports:
      self.ports.remove(port_id)

  def all_ports_except(self, dpid, in_port_id):
    return [p for p in self.ports[dpid] if p != in_port_id]

  def switch_not_yet_connected(self):
    return self.ports == {}

  def is_dirty(self):
    return self.dirty

  def set_dirty(self):
    self.dirty = True

  def clear_dirty(self):
    self.dirty = False
