import sys
import pygraphviz as pgv
import networkx as nx

class NetworkInformationBaseFromFile():

  # hosts is a dictionary of MAC addresses to (dpid, port) tuples
  #  { "11:11:11:11:11:11": (1234867, 1) ...}
  hosts = {}

  # dictionary of live ports on each switch
  # { 18237640987: [1,2], ...}
  ports = {}

  core_switches = set()
  edge_switches = set()

  # The internal ports are a dictionary of dpids to ports.  The ports
  # list here will end up being a subset of ports[dpid]
  # { 18237640987: [1,2], ...}
  switch_internal_ports = {}

  # Like switches but returns a dictionary of destination switches to ports.  
  # Though this data is part of the agraph, the conversion of agraphs to networkx 
  # graphs turns the source and destination of the edges around (which is OK, 
  # because the graph is undirected)
  port_mappings = {}

  # TODO
  dpid_to_switch_dict = {}
  switch_to_dpid_dict = {}

  def __init__(self, logger, topology_file="multiswitch_topo.dot"):
    self.logger = logger

    self.logger.info("---> Reading Topology from "+topology_file)
    self.agraph = pgv.AGraph(topology_file)
    switch_to_dpid_dict = {}
    for sw in self.agraph.nodes():
      dpid = int(sw.attr['dpid'])
      self.switch_to_dpid_dict[ str(sw) ] = dpid
      self.dpid_to_switch_dict[ dpid ] = str(sw)

    # It's faster to denormalize this now
    self.logger.info("---> Remembering internal ports")
    self.switch_internal_ports = { self.switch_to_dpid_dict[sw]: set([]) for sw in self.switch_to_dpid_dict }
    for e in self.agraph.edges():
      # Parse the source and destination switches
      source_dpid = int(e[0])
      #source_dpid = self.switch_to_dpid_dict[source_sw]
      dest_dpid = int(e[1])
      #dest_dpid = self.switch_to_dpid_dict[dest_sw]

      source_port = int(e.attr["src_port"])
      dest_port = int(e.attr["dport"])

      # Add a mapping for the forward directions source->dest
      self.switch_internal_ports[ source_dpid ].add( source_port )
      if source_dpid not in self.port_mappings:
        self.port_mappings[source_dpid] = {}
      self.port_mappings[source_dpid][dest_dpid] = source_port

      # Add a mapping for the reverse direction dest->source
      self.switch_internal_ports[ dest_dpid ].add( dest_port )
      if dest_dpid not in self.port_mappings:
        self.port_mappings[dest_dpid] = {}
      self.port_mappings[dest_dpid][source_dpid] = dest_port

    # Calculate the core/edge distinction.  Edge switches have only one 
    # connection to another switch
    for sw in self.port_mappings:
      if len(self.port_mappings[sw]) == 1:
        self.edge_switches.add(sw)
      else:
        self.core_switches.add(sw)

    self.logger.info("---> Calculating spanning tree")
    nxgraph = nx.from_agraph(self.agraph)
    self.nx_topo = nx.minimum_spanning_tree(nxgraph)    
    nx.write_edgelist(self.nx_topo, sys.stdout)

  def core_switch_dpids(self):
    return list(self.core_switches)

  def edge_switch_dpids(self):
    return list(self.edge_switches)

  def core_port_for_edge_dpid(self, dpid):
    return self.port_for_dpid[dpid]

  def next_hop_port(self, mac, core_dpid):
    return self.port_mappings[mac][core_dpid]

  def uplink_port_for_dpid(self, dpid):
    # Edge switches have only one entry in port_mappings[dpid], so we get it here
    connected_sw = self.port_mappings[dpid].keys()[0]
    return self.port_mappings[dpid][connected_sw]

  def is_internal_port(self, dpid, port_id):
    return dpid in self.core_switches or port_id == self.uplink_port_for_dpid(dpid)

  def learn(self, mac, dpid, port_id):
    # Do not learn a mac twice
    if mac in self.hosts:
      return

    # Compute next hop table: from each switch, which port do you need to go next to get to destination?
    self.nx_topo.add_node(mac)
    # To add the edge, you need to convert the dpid (e.g. 1) to a switch name (e.g s1)
    dpid_str = str(dpid)
    self.nx_topo.add_edge(dpid_str, mac)
    # Note we don't need a mapping from mac to switch because we never see packets going INTO a host
    self.port_mappings[dpid][mac] = port_id

    # Return shortest paths from each source in the graph to mac in the form 
    # [ src: to1, from2: to2 ..., to[n]: dest ]
    spaths = nx.shortest_path(self.nx_topo, None, mac, None)
    self.logger.info(str(spaths))
    next_hop_table = { }
    for dpid in self.ports.keys():
      # Convert dpid to a switch name, which is used in the graph
      sw = self.dpid_to_switch_dict[dpid] 
      # If there are no paths from sw, just skip it
      if sw in spaths:
        next_sw = spaths[sw][1]  # element 0 is the start, element 1 is the next hop
        # Convert this back to a dpid
        next_dpid = int(next_sw)
        # The next hop switch along the shortest path from sw to mac.  Possble that dest = mac
        next_hop_table[dpid] = self.port_mappings[dpid][next_dpid]

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

  def all_ports_except(self, dpid, in_port_id):
    return [p for p in self.ports[dpid] if p != in_port_id]

  def switch_not_yet_connected(self):
    return self.ports == {}

