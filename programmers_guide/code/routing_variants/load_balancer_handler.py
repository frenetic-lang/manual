import sys
sys.path.append("../routing")
from router_handler import *

class LoadBalancerHandler(RouterHandler):

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

  def pred_for_load_balancer(self):
    frontend_pred = IP4DstEq(self.nib.lb_frontend_ip())
    backend_pred = Or([IP4SrcEq(backend_ip) for backend_ip in self.nib.lb_backend_ips()])
    return frontend_pred | backend_pred 

  def policy(self):
    return Filter( SwitchEq(self.nib.router_dpid)) >> \
      IfThenElse( 
        self.pred_for_load_balancer(),
        SendToController("router"),
        self.policy_for_router() | self.policy_for_arp()
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
        sn = self.nib.subnet_for(frontend_ip)
        backend_ip = nib.backend_ip(src_ip)
        backend_mac = nib.mac_for_ip(backend_ip)
        if backend_mac == None:
          self.where_is(backend_ip)
        else:
          self.logger.info("Rerouting request for "+frontend_ip+" to "+backend_ip+"/"+backend_mac)
          self.logger.info("Using subnet on router port "+str(sn.router_port)+" mac "+sn.router_mac)
          actions = [
            SetIP4Dst(backend_ip),           
            SetEthSrc(sn.router_mac),
            SetEthDst(backend_mac),
            SetPort(sn.router_port)
          ]
          self.main_app.pkt_out(pkt.switch, payload, actions)

        # We consider the packet processed even if we don't know the mac 
        lb_processed = True        

      # If the packet is coming from a back-end IP, rewrite it with
      # the front-end IP.  
      if src_ip in nib.lb_backend_ips():
        dst_mac = nib.mac_for_ip(dst_ip)
        if dst_mac == None:
          self.where_is(dst_ip)
        else:
          sn = nib.subnet_for(dst_ip)
          self.logger.info("Rewriting reply from "+src_ip+" to "+frontend_ip)
          actions = [
            SetIP4Src(frontend_ip),           
            SetEthSrc(sn.router_mac),
            SetEthDst(dst_mac),
            SetPort(sn.router_port)
          ]
          self.main_app.pkt_out(pkt.switch, payload, actions)
        lb_processed = True        

    # Punt all non-load balancer packets to the router
    if not lb_processed:
      super(LoadBalancerHandler,self).packet_in(pkt, payload)