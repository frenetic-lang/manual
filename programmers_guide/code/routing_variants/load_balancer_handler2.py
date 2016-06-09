import sys
sys.path.append("../routing")
from router_handler import *

class LoadBalancerHandler2(RouterHandler):

  def where_is(self, src_ip):
    sn = self.nib.subnet_for(src_ip)
    self.logger.info("Sending out ARP Request for IP "+src_ip)
    self.arp_request(self.nib.router_dpid, sn.router_port, sn.router_mac, sn.gateway, src_ip)

  def connected(self):
    # We send out ARP requests to all back-end IP's so we minimize waiting
    # for first-time requests
    self.logger.info("Sending out ARP Requests to all Backend IPs")
    for backend_ip in self.nib.lb_backend_ips():
      self.where_is(backend_ip)

  def pred_for_assigned_clients(self):
    frontend_ip = self.nib.lb_frontend_ip()
    preds = []
    for (client_ip, backend_ip) in self.nib.backend_map.iteritems(): 
      # Forward direction: client -> front-end IP
      preds.append(IP4SrcEq(client_ip) & IP4DstEq(frontend_ip))
      # Backward direction: back-end IP -> client
      preds.append(IP4SrcEq(backend_ip) & IP4DstEq(client_ip))
    return Or(preds)

  def request_policy(self, backend_ip):
    sn = self.nib.subnet_for(backend_ip)
    dst_mac = self.nib.mac_for_ip(backend_ip)
    if dst_mac == None:
      return None
    return Seq([
      SetIP4Dst(backend_ip),
      SetEthSrc(sn.router_mac),
      SetEthDst(dst_mac),
      SetPort(sn.router_port)
    ])

  def response_policy(self, client_ip):
    frontend_ip = self.nib.lb_frontend_ip()
    sn = self.nib.subnet_for(client_ip)
    dst_mac = self.nib.mac_for_ip(client_ip)
    if dst_mac == None:
      return None
    return Seq([
      SetIP4Src(frontend_ip),
      SetEthSrc(sn.router_mac),
      SetEthDst(dst_mac),
      SetPort(sn.router_port)
    ])

  def assigned_clients_policy(self):
    frontend_ip = self.nib.lb_frontend_ip()
    pols = []
    for (client_ip, backend_ip) in self.nib.backend_map.iteritems(): 
      # Forward direction: client -> front-end IP
      pols.append(
        Filter(IP4SrcEq(client_ip) & IP4DstEq(frontend_ip)) >> \
        self.request_policy(backend_ip)
      )
      # Backward direction: back-end IP -> client
      pols.append(
        Filter(IP4SrcEq(backend_ip) & IP4DstEq(client_ip)) >> \
        self.response_policy(client_ip)
      )
    return Union(pols)

  def pred_for_unassigned_clients(self):
    frontend_pred = IP4DstEq(self.nib.lb_frontend_ip())
    backend_pred = Or([IP4SrcEq(backend_ip) for backend_ip in self.nib.lb_backend_ips()])
    return frontend_pred | backend_pred 

  def policy(self):
    return Filter( SwitchEq(self.nib.router_dpid)) >> \
      IfThenElse( 
        self.pred_for_assigned_clients(),
        self.assigned_clients_policy(),
        IfThenElse(
          self.pred_for_unassigned_clients(),
          SendToController("router"),
          self.policy_for_router() | self.policy_for_arp()
        )
      )

  def packet_in(self, pkt, payload):
    nib = self.nib

    # If we haven't learned the ports yet, just exit prematurely
    if nib.switch_not_yet_connected():
      return

    # If this packet was not received at the router, just ignore
    if pkt.switch != self.nib.router_dpid:
      return

    src_mac = pkt.ethSrc
    dst_mac = pkt.ethDst

    lb_processed = False
    if pkt.ethType == 0x800:  # IP 
      src_ip = pkt.ip4Src
      dst_ip = pkt.ip4Dst

      # If the packet is bound for a front-end IP, rewrite it to the
      # back end IP
      frontend_ip = self.nib.lb_frontend_ip()
      if dst_ip == frontend_ip:
        backend_ip = nib.backend_ip(src_ip)
        request_policy = self.request_policy(backend_ip)
        if request_policy == None:
          self.logger.error("Ooops can't find MAC of frontend IP")
          self.where_is(backend_ip)
        else:
          self.main_app.pkt_out(pkt.switch, payload, request_policy)

        # We consider the packet processed even if we don't know the mac 
        lb_processed = True        

      # If the packet is coming from a back-end IP, rewrite it with
      # the front-end IP.  
      if src_ip in nib.lb_backend_ips():
        response_policy = self.response_policy(src_ip)
        if response_policy == None:
          self.where_is(dst_ip)
        else:
          self.main_app.pkt_out(pkt.switch, payload, response_policy)
        lb_processed = True        

    # Punt all non-load balancer packets to the router
    if not lb_processed:
      super(LoadBalancerHandler2,self).packet_in(pkt, payload)