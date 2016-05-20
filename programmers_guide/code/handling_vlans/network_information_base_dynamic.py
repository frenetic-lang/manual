class NetworkInformationBaseDynamic(object):

  # hosts is a dictionary of MAC addresses to ports
  #  { "11:11:11:11:11:11": 2, ...}
  hosts = {}

  # ports on switch
  ports = []

  def __init__(self, logger):
    self.logger = logger

  def learn(self, mac, port_id, vlan):
    # Do not learn a mac twice
    if mac in self.hosts:
      return

    self.hosts[mac] = port_id
    if vlan not in self.vlans:
      self.vlans[vlan] = []
    self.vlans[vlan].append(port_id)
    self.logger.info(
      "Learning: "+mac+" attached to ( "+str(port_id)+" ), VLAN "+str(vlan)
    )

  def unlearn(self, mac):
    if mac in self.hosts:
      del self.hosts[mac]

  def port_for_mac(self, mac):
    if mac in self.hosts:
      return self.hosts[mac]
    else:
      return None

  def mac_for_port(self, port_id):
    for mac in self.hosts:
      if self.hosts[mac] == port_id:
        return mac
    return None

  def all_mac_port_pairs(self):
    return [ (mac, self.hosts[mac]) for mac in self.hosts.keys() ]

  def all_learned_macs(self):
    return self.hosts.keys()

  def set_ports(self, list_p):
    self.ports = list_p

  def add_port(self, port_id):
    if port_id not in ports:
      self.ports.append(port_id)

  def delete_port(self, port_id):
    if port_id in ports:
      self.ports.remove(port_id)
      for vl in self.vlans:
        if port_id in self.vlans[vl]:
          self.vlans[vl].remove(port_id)

  def switch_not_yet_connected(self):
    return self.ports == [] 

# VLAN Handling, dynamic version
  # vlans is a dictionary of VLANs to lists of ports
  #  { "1001": [1,3], "1002": [2,4] ...}

  vlans = {} 

  def vlan_of_port(self, port_id):
    for vl in self.vlans:
      if port_id in self.vlans[vl]:
        return vl
    return None

  def ports_in_vlan(self, vlan):
    return self.vlans[vlan] if vlan in self.vlans else None

  def all_vlan_ports_except(self, vlan, in_port_id):
    return [ p for p in self.ports_in_vlan(vlan) if p != in_port_id ]
