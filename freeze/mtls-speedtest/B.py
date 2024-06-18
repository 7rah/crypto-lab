# 服务器

# 监听 '127.0.0.1:4000'

import socket
import time
import config

from mtls import MTLS 
import crypto


server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind(config.server_addr)

server.listen(5)

RSA = crypto.RSA('key/B_pub.pem', 'key/B_pri.pem', 'key/A_pub.pem')

while True:
    conn, addr = server.accept()
    print('Connected by', addr)
    
    conn = MTLS(RSA,conn)
    conn.handshake()

    cnt = 0
    total_len = 0
    time_prev = time.time()
    while True:
        data = conn.recv()
        cnt += 1
        total_len += len(data)
        if time.time() - time_prev > 1:
            print('Speed:', total_len / 1024 / 1024, 'MB/s')
            total_len = 0
            time_prev = time.time()

