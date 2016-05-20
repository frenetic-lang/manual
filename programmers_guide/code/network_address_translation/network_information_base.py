from datetime import datetime

class Flow(object):
  INCOMING = 0
  OUTGOING = 1

  def __init__(self, src_ip, src_tcp_port, dst_ip, dst_tcp_port, direction):
    self.src_ip = src_ip
    self.src_tcp_port = src_tcp_port
    self.dst_ip = dst_ip
    self.dst_tcp_port = dst_tcp_port
    self.direction = direction

  # Note we don't include direction because it's derived from the others
  def __hash__(self):
    return hash((self.src_ip, self.src_tcp_port, self.dst_ip, self.dst_tcp_port))

  def __eq__(self, other):
    return (self.src_ip, self.src_tcp_port, self.dst_ip, self.dst_tcp_port) == \
      (other.src_ip, other.src_tcp_port, other.dst_ip, other.dst_tcp_port)

class NetworkInformationBase(object):
  dpid = None

  # In a real network, this would be dynamically configured
  router_port = 5
  visible_ip = "10.0.2.15"
  visible_mac = "08:00:27:94:44:d6"  # TODO: This should be dynamic, really

  # This is a dictionary of flows we've seen:
  # Flow() => ( visible_tcp_port, creation_time )
  flows = {}

  # Remember IP-to-source port and mac mappings for the return packet. 
  # src_ip => ( port, mac )
  ips = { }

  # When we need a new externally visible port, we grab one from this set
  visible_tcp_port_bag = set( range(50000, 59999) )

  def __init__(self, logger):
    self.logger = logger
    # We pre-seed the ip table with this info to make it easy.
    self.ips[self.visible_ip] = (self.router_port, self.visible_mac)

  def connected(self, dpid):
    self.dpid = dpid

  def learn(self, src_port_id, src_mac, flow):
    # First make sure this flow has not been learned already
    if flow in self.flows:
      return False   # Signal that we don't need to regenerate policy

    # Don't learn flows coming in from the router port.  If the flow originated 
    # from an internal IP, there should already be a reverse rule.  
    if src_port_id == self.router_port:
      return False

    # Remember port and mac of the source IP
    if not flow.src_ip in self.ips:
      self.ips[flow.src_ip] = ( src_port_id, src_mac )

    # Pick an arbitrary port to use and remember it
    visible_tcp_port = self.visible_tcp_port_bag.pop()
    reverse_flow = Flow(flow.dst_ip, flow.dst_tcp_port, self.visible_ip, visible_tcp_port, Flow.INCOMING)
    self.flows[flow] = ( self.visible_ip, visible_tcp_port, datetime.now() )
    self.flows[reverse_flow] = ( flow.src_ip, flow.src_tcp_port, datetime.now() )

    msg = "Learning flow: ({0},{1}) => ({4},{5}) -> ({2},{3})".format(
      flow.src_ip, flow.src_tcp_port,
      flow.dst_ip, flow.dst_tcp_port,
      self.visible_ip, visible_tcp_port
    )
    self.logger.info(msg)
    return True

  def all_flows(self):
    return self.flows.keys()

  def rewrite_for_flow(self, flow):
    return self.flows[flow] if flow in self.flows else None

  def port_and_mac_of_ip(self, src_ip):
    return self.ips[src_ip] if src_ip in self.ips else None

  def harvest_outdated(self):
    # TODO: Remove all entries over 10 minutes old
    pass

  def switch_not_yet_connected(self):
    self.dpid == None