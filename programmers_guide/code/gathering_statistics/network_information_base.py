class NetworkInformationBase(object):

  # ports on switch
  ports = []

  def __init__(self, logger):
    self.logger = logger

  def set_dpid(self, dpid):
    self.dpid = dpid

  def get_dpid(self):
    return self.dpid

  def switch_not_yet_connected(self):
    return self.ports == [] 

  def set_ports(self, list_p):
    self.ports = list_p

  def add_port(self, port_id):
    if port_id not in ports:
      self.ports.append(port_id)

  def delete_port(self, port_id):
    if port_id in ports:
      self.ports.remove(port_id)

  def all_ports(self):
    return self.ports