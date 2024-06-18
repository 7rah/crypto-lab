# 服务器地址 127.0.0.1:4000

# 客户端
import socket
import config
from mtls import MTLS 
import crypto

# 初始化 RSA 对象
RSA = crypto.RSA('key/A_pub.pem', 'key/A_pri.pem', 'key/B_pub.pem')

# 1. 连接服务器
conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
conn.connect(config.server_addr)

conn = MTLS(RSA,conn)
conn.handshake()

# 初始化 data 为 1MB 的数据
data = b'1'*1024*1024
while True:
    # 2. 发送数据
    conn.send(data)