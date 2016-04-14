class NetworkInformationBase():

  # hosts is a dictionary of MAC addresses to ports
  #  { "11:11:11:11:11:11": 2, ...}
  hosts = {}

  # ports on switch
  ports = []

  def __init__(self, logger):
    self.logger = logger

  def learn(self, mac, port):
    # Do not learn a mac twice
    if mac in self.hosts:
      return

    self.hosts[mac] = port
    self.logger.info(
      "Learning: "+mac+" attached to ( "+str(port)+" )"
    )

  def port_for_mac(self, mac):
    if mac in self.hosts:
      return self.hosts[mac]
    else:
      return None

  def all_mac_port_pairs(self):
    return [ (mac, self.hosts[mac]) for mac in self.hosts.keys() ]

  def all_learned_macs(self):
    return self.hosts.keys()

  def set_ports(self, list_p):
    self.ports = list_p

  def add_port(self, p):
    if p not in ports:
      self.ports.append(p)

  def delete_port(self, p):
    if p in ports:
      self.ports.remove(p)

  def all_ports_except(self, in_port):
    return [p for p in self.ports if p != in_port]