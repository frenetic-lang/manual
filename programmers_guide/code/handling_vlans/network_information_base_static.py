class NetworkInformationBaseStatic(object):

  # hosts is a dictionary of MAC addresses to ports
  #  { "11:11:11:11:11:11": 2, ...}
  hosts = {}

  # ports on switch
  ports = []

  def __init__(self, logger):
    self.logger = logger

  def learn(self, mac, port_id):
    # Do not learn a mac twice
    if mac in self.hosts:
      return

    self.hosts[mac] = port_id
    self.logger.info(
      "Learning: "+mac+" attached to ( "+str(port_id)+" )"
    )

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

  def unlearn(self, mac):
    if mac in self.hosts:
      del self.hosts[mac]

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

# VLAN Handling, 
  def switch_not_yet_connected(self):
    return self.ports == [] 
    
  def vlan_of_port(self, port_id):
    return 1001 if port_id % 2 == 1 else 1002

  def ports_in_vlan(self, vlan):
    ports_have_remainder = 1 if vlan == 1001 else 0 
    return [ p for p in self.ports if p % 2 == ports_have_remainder ]

  def all_vlan_ports_except(self, vlan, in_port_id):
    return [ p for p in self.ports_in_vlan(vlan) if p != in_port_id ]
