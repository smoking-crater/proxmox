#################################################################################
#
# script to read the proxmox API via the proxmoxer wrapper to generate an Ansible inventory file based on tags
#
#
#################################################################################
from proxmoxer import ProxmoxAPI
import socket
from dotenv import load_dotenv
import os



#add the IP's, only ONE per cluster
servers = ['192.168.0.73','192.168.1.49']

#what tags are you wanting to look for an put into inventory?
tags = ['centos','debian','windows']

#username/pwd of your clusters should go into a .env file
load_dotenv()
username=os.getenv("username")
password=os.getenv("password")

#output file, include full path if you want it
f = open("inventory","w")

lxc = []


# first create a group called [proxmox] in the inventory.  DNS must resolve the node names otherwise will fail
f.write('[proxmox]\n')
print('[proxmox]')
for server in servers:
    proxmox = ProxmoxAPI(server, user=username, password=password, verify_ssl=False)
    nodes = proxmox.nodes.get()
    for node in nodes:
        node_name = node['node']
        try:
            ip_address = socket.gethostbyname(node_name)
        except socket.gaierror:
            ip_address = ''
        print(ip_address)
        f.write(ip_address+'\n')

for tag in tags:
    print('[' + tag + ']')
    f.write('[' + tag + ']\n')
    for server in servers:
        proxmox = ProxmoxAPI(server, user=username, password=password, verify_ssl=False)
        for node in proxmox.nodes.get():
            node_name = node['node']
            for vm in proxmox.nodes(node_name).qemu.get():
                tagvar = 'tags'
                mytag = vm.get(tagvar,0)
                if tag in str(mytag):
                    vmid = vm['vmid']
                    try:
                        net_info = proxmox.nodes(node_name).qemu(vmid).agent.get("network-get-interfaces")
                        for iface in net_info.get("result", []):
                            for addr in iface.get("ip-addresses", []):
                                if addr['ip-address-type'] == 'ipv4':
                                    if '192.168' in str(addr['ip-address']):
                                         print(addr['ip-address'])
                                         f.write(addr['ip-address']+'\n')
                    except Exception as e:
                        print(f"Could not retrieve IP for VM {vmid}: {e}")

        #now run through the LXC's
        for node in proxmox.nodes.get():
            node_name = node['node']
            for vm in proxmox.nodes(node_name).lxc.get():
                tagvar = 'tags'
                mytag = vm.get(tagvar,0)
                if tag in str(mytag):
                    vmid = vm['vmid']
                    try:
                        net_info = proxmox.nodes(node_name).lxc(vmid).config.get()
                        if 'net0' in net_info:
                            ip_info = net_info['net0'].split(',')
                            for item in ip_info:
                                if item.startswith('ip='):
                                    ip = item.split('=')[1].split('/')[0]
                                    if '192.168' in ip:
                                         print(ip)
                                         lxc.append(ip)
                                         f.write(ip+'\n')
                    except Exception as e:
                        print(f"Could not retrieve IP for VM {vmid}: {e}")

#now print out the containers
print("[containers]")
f.write("[containers]\n")
for x in lxc:
    print(x)
    f.write(x+'\n')
f.close()
