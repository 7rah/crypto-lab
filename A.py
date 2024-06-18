# 服务器地址 127.0.0.1:4000

# 客户端
import socket
import config
from mtls import MTLS 
import crypto
import file_transfer

# 初始化 RSA 对象
RSA = crypto.RSA('key/A_pub.pem', 'key/A_pri.pem', 'key/B_pub.pem')

# 1. 连接服务器
conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
conn.connect(config.server_addr)

conn = MTLS(RSA,conn)
conn.handshake()

#file = "/home/chez/download/metasploitable-linux-2.0.0.zip"
#file = "/home/chez/download/ungoogled-chromium_124.0.6367.60-1_linux.tar" 
#file = "/home/chez/download/firefox-125.0.1.source.tar"
# 读取命令行参数
import sys
file = sys.argv[1]
client = file_transfer.UploadClient(file,io=conn)

client.handshake()
client.send_file()
