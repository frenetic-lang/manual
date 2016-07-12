import sys
import pygraphviz as pgv
import networkx as nx

class NetworkInformationBaseFromFile(object):

  # hosts is a dictionary of MAC addresses to (dpid, port) tuples
  #  { "11:11:11:11:11:11": (1234867, 1) ...}
  hosts = {}

  # dictionary of live ports on each switch
  # { 18237640987: [1,2], ...}
  ports = {}

  core_switches = set()
  edge_switches = set()

  # Uplink port from each edge switch to the nearest core switch
  uplink_port = {}

  # For each switch, returns a dictionary of destination switches to ports.  
  # So in the following, a packet in 18237640987 can get to switch 9287354
  # by going out port 7.  This effectively turns the undirected edges of the
  # topo graph into bidirectional edges.  Later we'll add learned MAC addresses
  # to this dictionary as well.
  #  { 18237640987: { 9287354: 7, 09843509: 5, ... }}
  port_mappings = {}

  # On core switches, we pretend that edges not living on the spanning 
  # tree are disabled - we don't send or flood traffic to it, and we drop
  # all incoming traffic from it.  So this structure keeps track of all
  # ports that are enabled - each enabled_ports[sw] is a subset of ports[sw]
  enabled_ports = {}

  def add_port_mapping(self, from_node, to_node, on_port):
    if from_node not in self.port_mappings:
      self.port_mappings[from_node] = {}
    self.port_mappings[from_node][to_node] = on_port

  def __init__(self, logger, topology_file="multiswitch_topo.dot"):
    self.logger = logger

    self.logger.info("---> Reading Topology from "+topology_file)
    self.agraph = pgv.AGraph(topology_file)

    # It's faster to denormalize this now
    self.logger.info("---> Remembering internal ports")
    switches = [ int(sw) for sw in self.agraph.nodes()]
    for e in self.agraph.edges():
      # Parse the source and destination switches
      source_dpid = int(e[0])
      dest_dpid = int(e[1])
      source_port = int(e.attr["src_port"])
      dest_port = int(e.attr["dport"])

      # Add a mapping for the forward directions source->dest
      self.add_port_mapping(source_dpid, dest_dpid, source_port)

      # Add a mapping for the reverse direction dest->source
      self.add_port_mapping(dest_dpid, source_dpid, dest_port)

    # Calculate the core/edge attribute.  Edge switches have only one 
    # connection to another switch
    for sw in self.port_mappings:
      if len(self.port_mappings[sw]) == 1:
        self.edge_switches.add(sw)
        # Edge switches have only one entry in port_mappings[dpid], so we get it here
        connected_sw = self.port_mappings[sw].keys()[0]
        self.uplink_port[sw] = self.port_mappings[sw][connected_sw]
      else:
        self.core_switches.add(sw)

    self.logger.info("---> Calculating spanning tree")
    nxgraph = nx.from_agraph(self.agraph)
    self.nx_topo = nx.minimum_spanning_tree(nxgraph)    
    nx.write_edgelist(self.nx_topo, sys.stdout)

    self.logger.info("---> Enabling only those ports on the spanning tree")
    for (from_dpid, to_dpid) in self.nx_topo.edges():
      # We look up the port mapping from the port-mapping dictionary instead of 
      # from the graph attributes because NetworkX flips the src and dest node
      # arbitrarily in an undirected graph
      from_dpid_int = int(from_dpid)
      to_dpid_int = int(to_dpid)
      from_port = self.port_mappings[from_dpid_int][to_dpid_int]
      if from_dpid_int not in self.enabled_ports:
        self.enabled_ports[from_dpid_int] = []
      self.enabled_ports[from_dpid_int].append(from_port)

      to_port = self.port_mappings[to_dpid_int][from_dpid_int]
      if to_dpid_int not in self.enabled_ports:
        self.enabled_ports[to_dpid_int] = []
      self.enabled_ports[to_dpid_int].append(to_port)

  def core_switch_dpids(self):
    return list(self.core_switches)

  def edge_switch_dpids(self):
    return list(self.edge_switches)

  def core_port_for_edge_dpid(self, dpid):
    return self.port_for_dpid[dpid]

  def next_hop_port(self, mac, core_dpid):
    return self.hosts[mac][2][core_dpid]

  def uplink_port_for_dpid(self, dpid):
    return self.uplink_port[dpid]

  def is_internal_port(self, dpid, port_id):
    return (dpid in self.core_switches) or (port_id == self.uplink_port_for_dpid(dpid))

  def switches(self):
    return self.ports.keys()

  def learn(self, mac, dpid, port_id):
    # Do not learn a mac twice
    if mac in self.hosts:
      return

    # Compute next hop table: from each switch, which port gets you closer to destination?
    self.nx_topo.add_node(mac)
    dpid_str = str(dpid)
    self.nx_topo.add_edge(dpid_str, mac)
    # Note we don't need a mapping from mac to switch - we never see this hop
    self.port_mappings[dpid][mac] = port_id

    # Return shortest paths from each source in the graph to mac in the form 
    # [ src: to1, from2: to2 ..., to[n]: dest ]
    spaths = nx.shortest_path(self.nx_topo, None, mac, None)
    next_hop_table = { }
    for from_dpid in self.switches():
      # If we're on the switch the Mac is connected to, just add the next_hop
      if from_dpid == dpid:
        next_hop_table[from_dpid] = port_id
      else:
        sw = str(from_dpid)
        # If there are no paths from sw, just skip it
        if sw in spaths:
          next_sw = spaths[sw][1]  # element 0 is the start, element 1 is the next hop
          # Convert this back to a dpid
          next_dpid = int(next_sw)
          # The next hop switch along the shortest path from sw to mac.
          next_hop_table[from_dpid] = self.port_mappings[from_dpid][next_dpid]

    cd = (dpid, port_id, next_hop_table)
    self.hosts[mac] = cd
    self.logger.info("Learning: "+mac+" attached to "+str(cd))

  def port_for_mac_on_switch(self, mac, dpid):
    return self.hosts[mac][1] \
      if mac in self.hosts and self.hosts[mac][0] == dpid else None

  def mac_for_port_on_switch(self, dpid, port_id):
    for mac in self.hosts:
      if self.hosts[mac][0] == dpid and self.hosts[mac][1] == port_id:
        return mac
    return None

  def unlearn(self, mac):
    if mac in self.hosts:
      del self.hosts[mac]

  def all_mac_port_pairs_on_switch(self, dpid):
    return [ 
      (mac, self.hosts[mac][1]) 
      for mac in self.hosts.keys() if self.hosts[mac][0] == dpid 
    ]

  def all_learned_macs_on_switch(self, dpid):
    return [
      mac for mac in self.hosts.keys() if self.hosts[mac][0] == dpid 
    ]

  def all_learned_macs(self):
    return self.hosts.keys()

  def all_mac_dpid_pairs(self):
    return [ 
      (mac, self.hosts[mac][0]) for mac in self.hosts.keys()
    ]

  def set_all_ports(self, switch_list):
    self.ports = switch_list

  def add_port(self, dpid, port_id):
    if port_id not in self.ports[dpid]:
      self.ports.append(port_id)

  def delete_port(self, dpid, port_id):
    if port_id in self.ports:
      self.ports.remove(port_id)

  def all_enabled_ports_except(self, dpid, in_port_id):
    ports_to_flood = self.enabled_ports[dpid] if dpid in self.core_switches else self.ports[dpid]
    return [p for p in ports_to_flood if p != in_port_id]

  def switch_not_yet_connected(self):
    return self.ports == {}

