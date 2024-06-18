import crypto
import time
import os
from config import TIME_DIFF
#global socket_state
#socket_state = 'normal'
#def signal_handler(signal, frame):
#    socket_state = 'close'
#    time.sleep(1.5)
#    print('You pressed Ctrl+C!')
#    sys.exit(0)
#
#signal.signal(signal.SIGINT, signal_handler)



# 下面的长度都是字节长度，包括长度字段本身

# 客户端
# 1. 发送 diffie-hellman 公钥，用 RSA 签名
# | length(4)       | 
# | timestamp(4)    |
# | DH 公钥(256)    |
# | RSA 签名(256)   |

# 服务端
# 1. 发送 diffie-hellman 公钥，用 RSA 签名
# | length(4)       |
# | timestamp(4)    |
# | DH 公钥(256)    |
# | RSA 签名(256)   |

# 双方通过 diffie-hellman 生成了共享密钥,RSA 保证了 DH 公钥的安全性
# 这里即使 RSA 私钥泄露，也不会影响 DH 公钥的安全性
# 同时，RSA 也保证了 DH 公钥的完整性，防止中间人攻击


class KeyExchange:
    def __init__(self,RSA):
        self.dh = crypto.DH()
        self.RSA = RSA

    
    def pack(self):
        # length 
        length = 4 + 4 + 256 + 256
        length = length.to_bytes(4,byteorder='big')
        
        # timestamp
        timestamp = int(time.time())
        #print('timestamp:',timestamp)
        timestamp = timestamp.to_bytes(4,byteorder='big')

        dh_pub_key = self.dh.get_public_key()
        signature = self.RSA.sign(length + timestamp + dh_pub_key)
        return length + timestamp + dh_pub_key + signature
    
    def gen_shared_key(self,data):
        length = data[:4]
        timestamp = data[4:8]
        dh_pub_key = data[8:256+8]
        signature = data[256+8:]

        # 验证 timestamp，确保时间差在 TIME_DIFF 之内
        if abs(int.from_bytes(timestamp,byteorder='big') - time.time()) > TIME_DIFF:
            print('时间戳验证失败')
            return None

        if not self.RSA.verify(length + timestamp + dh_pub_key,signature):
            print('DH 公钥验证失败')
            return None
        
        return self.dh.gen_shared_key(dh_pub_key)
    
def test_KeyExchange():
    A = crypto.RSA('key/A_pub.pem', 'key/A_pri.pem', 'key/B_pub.pem')
    B = crypto.RSA('key/B_pub.pem', 'key/B_pri.pem', 'key/A_pub.pem')

    k_a = KeyExchange(A)
    k_b = KeyExchange(B)

    data_a = k_a.pack()
    data_b = k_b.pack()

    shared_key_a = k_a.gen_shared_key(data_b)
    shared_key_b = k_b.gen_shared_key(data_a)

    print(shared_key_a == shared_key_b)


# 密钥交换完成后，双方使用共享密钥进行通信
# record 的数据格式为
# | length(4)        |
# | timestamp(4)     |
# | sequence(4)      |
# | random_number(4) |
# | encrypted_data   | # 使用 AES-256-CCM 加密，密钥为共享密钥，随机数为 timestamp(4) + sequence(4) + random_number(4)
# | cmac(16)         | # AES-256-CBC-MAC，密钥为共享密钥，

class SendRecord:
    # 初始化，输入共享密钥
    def __init__(self,shared_key):
        self.sequence = 0
        self.AESCCM = crypto.AESCCM(shared_key)

    # 加密数据
    def encrypt(self,data):
        length = 4 + 4 + 4 + 4 + 16 + len(data)
        length = length.to_bytes(4,byteorder='big')

        timestamp = int(time.time())
        timestamp = timestamp.to_bytes(4,byteorder='big')

        sequence = self.sequence.to_bytes(4,byteorder='big')
        self.sequence += 1

        random_number = os.urandom(4)

        nonce = timestamp + sequence + random_number
        additional_data = length + timestamp + sequence + random_number

        encrypted_data =  self.AESCCM.encrypt(nonce,data,additional_data)

        return length + timestamp + sequence + random_number + encrypted_data


class RecvRecord:
    # 初始化，输入共享密钥
    def __init__(self,shared_key):
        self.sequence = 0
        self.AESCCM = crypto.AESCCM(shared_key)
        self.last_timestamp = None

    # 解密数据
    def decrypt(self,data):
        length = int.from_bytes(data[:4],byteorder='big')
        timestamp = int.from_bytes(data[4:8],byteorder='big')
        sequence = int.from_bytes(data[8:12],byteorder='big')
        random_number = data[12:16]


        nonce = data[4:16]
        additional_data = data[:16]
        encrypted_data = data[16:]

        try:
            # 确保整个数据包的完整性
            decrypted_data = self.AESCCM.decrypt(nonce,encrypted_data,additional_data)

            # 序列号只可能递增，如果不是递增，说明遭受重放攻击
            if sequence != self.sequence:
                raise Exception('序列号错误')
            self.sequence += 1


            # 时间戳与上一个数据包的时间戳比较，确保时间戳递增，防止重放攻击
            if self.last_timestamp is None:
                self.last_timestamp = timestamp
            else:
                if timestamp < self.last_timestamp:
                    raise Exception('时间戳错误')


        except Exception as e:
            raise Exception('解密失败')
        
        return decrypted_data




def do_send(io,data):
    return io.sendall(data)
def do_recv(io,length):
#    data = None
#    state = 0
#    while state == 0:
#        try:
#            data = io.recv(length)
#            state = 1
#        except Exception as e:
#            if socket_state == 'close':
#                io.close()
#            print('do_recv:',e)
#
#    state = 0
#    while len(data) < length:
#        try:
#            data += io.recv(length - len(data))
#        except Exception as e:
#            print('do_recv:',e)
#            if socket_state == 'close':
#                io.close()
#                break
#            if e.errno == 104:
#                print(1104)
#                io.close()
#                break
#            
#    return data
    

    data = io.recv(length)
    while len(data) < length:
        data += io.recv(length - len(data))
    return data


def fix_read(io):
    length_raw = do_recv(io,4)
    length = int.from_bytes(length_raw,byteorder='big')
    data = do_recv(io,length - 4)
    #print('fix_read:',len(data))
    return length_raw + data

class MTLS:
    def __init__(self,RSA,io):
        self.RSA = RSA
        self.key_exchange = KeyExchange(self.RSA)
        self.io = io
        self.shared_key = None
        self.send_record = None
        self.recv_record = None
        #io.settimeout(0.5)
    
    def handshake(self):
        # 发送 DH 公钥
        data = self.key_exchange.pack()
        do_send(self.io,data)

        # 读取对方端发送的 DH 公钥，计算共享密钥
        data = fix_read(self.io)
        shared_key = self.key_exchange.gen_shared_key(data)

        if shared_key is None:
            raise Exception('握手失败')
        self.shared_key = shared_key
        
        print('mTLS: DH 握手成功, 共享密钥为: ',f"{shared_key.hex()[:16]}...")

    def send(self,data):
        if self.send_record is None:
            self.send_record = SendRecord(self.shared_key)
        
        data = self.send_record.encrypt(data)
        do_send(self.io,data)
        
    def recv(self):
        if self.recv_record is None:
            self.recv_record = RecvRecord(self.shared_key)
        
        data = fix_read(self.io)
        return self.recv_record.decrypt(data)


