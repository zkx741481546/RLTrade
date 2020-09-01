import os
import paramiko
from paramiko import SSHClient
from scp import SCPClient

server_list = [('124.70.32.29', 22)]
abs_path =os.path.split(os.path.abspath(__file__))[:-1][0]
file = abs_path + '\\'
server_path = '/usr/zkx/Stable-BaselineTrading/PlotOutput/'
for ip, port in server_list:
    ssh = SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(hostname=ip,
                port=port,
                username='root',
                password='Hadoop0201')
    scp = SCPClient(ssh.get_transport())
    scp.get(server_path, file, recursive=True)