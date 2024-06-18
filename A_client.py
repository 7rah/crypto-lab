import socket
import crypto
import file_transfer
import config
from mtls import MTLS 
import _thread


# 初始化 RSA 对象
RSA = crypto.RSA('key/A_pub.pem', 'key/A_pri.pem', 'key/B_pub.pem')

def do_upload(file):
    # 1. 连接服务器
    conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    conn.connect(config.server_addr)

    conn = MTLS(RSA,conn)
    conn.handshake()

    client = file_transfer.UploadClient(file,io=conn)

    client.handshake()
    client.send_file()

# 监听 socket
server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind(config.client_addr)
server.listen(5)

while True:
    conn, addr = server.accept()
    print('Connected by', addr)
    file = conn.recv(1024)
    file = file.decode()

    try:
        # 用线程处理连接
        #process(conn)
        _thread.start_new_thread( do_upload, (file,) )

    except Exception as e:
        conn.close()
        print(e)
        continue

