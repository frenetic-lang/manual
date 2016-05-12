class NetworkInformationBase():

  # hosts is a dictionary of MAC addresses to (dpid, port) tuples
  #  { "11:11:11:11:11:11": (1234867, 1) ...}
  hosts = {}

  # dictionary of live ports on each switch
  # { "11:11:11:11:11:11": [1,2], ...}
  ports = {}

  # For this incarnation, we assume the switch with dpid = 1 is the core switch
  core_switch_dpid = 1

  def __init__(self, logger):
    self.logger = logger

  def switch_dpids(self):
    return [dpid for dpid in self.ports.keys() if dpid != self.core_switch_dpid]

  def learn(self, mac, dpid, port_id):
    # Do not learn a mac twice
    if mac in self.hosts:
      return

    cd = (dpid, port_id)
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

