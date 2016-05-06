class NetworkInformationBase():

  # hosts is a dictionary of MAC addresses to (switch, port) tuples
  #  { "11:11:11:11:11:11": (1,2) ...}
  hosts = {}

  # dictionary of live ports on each switch
  # { "11:11:11:11:11:11": [1,2], ...}
  ports = {}

  # Dirty flag set if policies need to be regenerated and sent to switches
  dirty = False

  # TODO: Derive this from configuration
  router_dpid = int("010000000000", 16)
  switch_dpids = [ int("010000000001", 16), int("010000000002", 16)]
  subnets = [ ("10.0.1.0", 24, 1), ("10.0.2.0", 24, 2) ] 
  router_mac = "01:00:00:00:00:00"

  def __init__(self, logger):
    self.logger = logger

  def learn(self, mac, dpid, port_id):
    # Do not learn a mac twice
    if mac in self.hosts:
      return

    self.hosts[mac] = (dpid, port_id)
    self.logger.info(
      "Learning: "+mac+" attached to ( "+str(dpid)+" , "+str(port_id)+" )"
    )
    self.set_dirty()

  def port_for_mac_on_switch(self, mac, dpid):
    return self.hosts[mac][1] if mac in self.hosts and self.hosts[mac][0] == dpid else None

  def mac_for_port_on_switch(self, dpid, port_id):
    for mac in self.hosts:
      if self.hosts[mac] == (dpid, port_id):
        return mac
    return None

  def all_learned_macs(self):
    return [ (mac, dpid, port_id) for (mac, (dpid,port_id)) in self.hosts.iteritems() ]

  def unlearn(self, mac):
    if mac in self.hosts:
      del self.hosts[mac]
      self.set_dirty()

  def all_mac_port_pairs_on_switch(self, dpid):
    return [ (mac, self.hosts[mac][1]) for mac in self.hosts.keys() if self.hosts[mac][0] == dpid ]

  def all_learned_macs_on_switch(self, dpid):
    return [mac for mac in self.hosts.keys() if self.hosts[mac][0] == dpid ]

  def set_all_ports(self, switch_list):
    self.ports = switch_list

  def set_ports(self, dpid, list_p):
    self.ports[dpid] = list_p

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
