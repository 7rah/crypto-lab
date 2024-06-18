# 服务器

# 监听 '127.0.0.1:4000'

import socket
import time
import config
import _thread

from mtls import MTLS 
import crypto
import file_transfer

# tcp 监听
server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind(config.server_addr)
server.listen(5)

RSA = crypto.RSA('key/B_pub.pem', 'key/B_pri.pem', 'key/A_pub.pem')

def process(conn):
    conn = MTLS(RSA,conn)
    conn.handshake()


    conn = file_transfer.UploadServer(conn)
    conn.handshake()
    conn.recv_file()


        



while True:
    conn, addr = server.accept()
    print('Connected by', addr)

    try:
        # 用线程处理连接
        #process(conn)
        _thread.start_new_thread( process, (conn,) )

    except Exception as e:
        conn.close()
        print(e)
        continue

