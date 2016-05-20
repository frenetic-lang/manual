import sys
sys.path.append("../routing")
from router_handler import *

class LoadBalancerHandler(RouterHandler):

  def connected(self):
    # We send out ARP requests to all back-end IP's so we minimize waiting
    # for first-time requests
    self.logger.info("Sending out ARP Requests to all Backend IPs")
    frontend_ip = self.nib.lb_frontend_ip()
    sn = self.nib.subnet_for(frontend_ip)
    for backend_ip in self.nib.lb_backend_ips():
      self.logger.info("Sending out ARP Requests to Backend IP "+backend_ip)
      self.arp_request(self.nib.router_dpid, sn.router_port, sn.router_mac, sn.gateway, backend_ip)

  def policy_for_load_balancer(self):
    frontend_pred = IP4DstEq(self.nib.lb_frontend_ip())
    backend_pred = Or([IP4SrcEq(backend_ip) for backend_ip in self.nib.lb_backend_ips()])

    return Filter(frontend_pred | backend_pred) >> SendToController("load_balancer")

  def policy(self):
    return Filter( SwitchEq(self.nib.router_dpid)) >> \
      Union( [ 
        self.policy_for_router(), 
        self.policy_for_load_balancer(),
        self.policy_for_arp() 
      ])

  def packet_in(self, dpid, port_id, payload):
    nib = self.nib

    # Parse the interesting stuff from the packet
    ethernet_packet = self.main_app.packet(payload, "ethernet")
    src_mac = ethernet_packet.src
    dst_mac = ethernet_packet.dst

    lb_processed = False
    if ethernet_packet.ethertype == ether_types.ETH_TYPE_IP:
      ip_packet = self.main_app.packet(payload,"ipv4")
      src_ip = ip_packet.src
      dst_ip = ip_packet.dst    

      # If the packet is bound for a front-end IP, rewrite it to the
      # back end IP
      frontend_ip = self.nib.lb_frontend_ip()
      if dst_ip == frontend_ip:
        sn = self.nib.subnet_for(frontend_ip)
        backend_ip = nib.backend_ip(src_ip)
        backend_mac = nib.mac_for_ip(backend_ip)
        if backend_mac == None:
          self.logger.error("Uh oh.  Don't know Mac for "+backend_ip)
        if backend_mac != None:
          self.logger.info("Rerouting request for "+frontend_ip+" to "+backend_ip+"/"+backend_mac)
          self.logger.info("Using subnet on router port "+str(sn.router_port)+" mac "+sn.router_mac)
          actions = [
            SetIP4Dst(backend_ip),           
            SetEthSrc(sn.router_mac),
            SetEthDst(backend_mac),
            Output(Physical(sn.router_port))
          ]
          self.main_app.pkt_out(dpid, payload, actions)
          lb_processed = True        

      # If the packet is coming from a back-end IP, rewrite it with
      # the front-end IP.  
      if src_ip in nib.lb_backend_ips():
        dst_mac = nib.mac_for_ip(dst_ip)
        if dst_mac == None:
          self.logger.error("Uh oh.  Don't know Mac for "+dst_ip)
        else:
          sn = nib.subnet_for(dst_ip)
          self.logger.info("Rewriting reply from "+src_ip+" to "+frontend_ip)
          actions = [
            SetIP4Src(frontend_ip),           
            SetEthSrc(sn.router_mac),
            SetEthDst(dst_mac),
            Output(Physical(sn.router_port))
          ]
          self.main_app.pkt_out(dpid, payload, actions)
          lb_processed = True        

    # Punt all non-load balancer packets to the router
    if not lb_processed:
      self.logger.info("Punting packet from "+src_mac+"->"+dst_mac+" to router module")
      super(LoadBalancerHandler,self).packet_in(dpid, port_id, payload)