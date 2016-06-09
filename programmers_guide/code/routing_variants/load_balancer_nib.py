import sys
sys.path.append("../routing")
from network_information_base import *

class LoadBalancerNIB(NetworkInformationBase):

  lb_config = {}

  # Map source IP's to a host so they stay sticky
  # { "10.0.1.2": "10.0.2.2", "10.0.1.3": "10.0.2.3" }
  backend_map = {}

  # index into lb_config["farm"] for the next target host
  current_backend_index= 0

  def __init__(self, logger, topo_file, routing_table_file, load_balancer_file):
    super(LoadBalancerNIB,self).__init__(logger, topo_file, routing_table_file)

    # Read the load_balancer configuration
    f = open(load_balancer_file, "r")
    self.lb_config = json.load(f)
    f.close()

  def backend_ip(self, src_ip):
    if src_ip not in self.backend_map:
      backends = self.lb_config["backends"]
      n_backends = len(backends)
      self.backend_map[src_ip] = backends[self.current_backend_index]
      self.current_backend_index = (self.current_backend_index + 1) % n_backends

    return self.backend_map[src_ip]

  def lb_frontend_ip(self):
    return self.lb_config["frontend"]

  def lb_backend_ips(self):
    return self.lb_config["backends"]