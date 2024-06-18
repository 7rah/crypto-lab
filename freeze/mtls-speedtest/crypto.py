import rsa
import pyDH

class RSA:
    # 初始化，输入公钥和私钥文件路径，并读取
    def __init__(self, self_pub_path, self_pri_path, other_pub_path):
        with open(self_pub_path, 'rb') as f:
            self.pub = rsa.PublicKey.load_pkcs1(f.read())
        with open(self_pri_path, 'rb') as f:
            self.pri = rsa.PrivateKey.load_pkcs1(f.read())
        with open(other_pub_path, 'rb') as f:
            self.other_pub = rsa.PublicKey.load_pkcs1(f.read())

    # 签名使用自己的私钥
    def sign(self, message):
        # 用 SHA-256 算法对消息进行签名
        return rsa.sign(message, self.pri, 'SHA-256')


    # 认证使用对方的公钥
    def verify(self ,message, signature):
        try:
            rsa.verify(message, signature, self.other_pub)
            return True
        except rsa.pkcs1.VerificationError:
            return False
    
    # 加密使用对方的公钥
    def encrypt(self, message):
        return rsa.encrypt(message, self.other_pub)
    
    # 解密使用自己的私钥
    def decrypt(self, message):
        return rsa.decrypt(message, self.pri)

class DH():
    def __init__(self):
        self.dh = pyDH.DiffieHellman()
    
    # 返回 DH 公钥，长度为 256 bytes，2048 bit，大端序
    def get_public_key(self):
        pub_key = self.dh.gen_public_key()
        return pub_key.to_bytes(256, byteorder='big')
    
    # 返回 共享密钥，长度为 32 bytes，256 bit
    def gen_shared_key(self, other_pubkey):
        other_pubkey = int.from_bytes(other_pubkey, byteorder='big')
        return self.dh.gen_shared_key(other_pubkey)


import cryptography.hazmat.primitives.ciphers.aead
class AESCCM:
    def __init__(self,key):
        self.key = key
        self.aes = cryptography.hazmat.primitives.ciphers.aead.AESCCM(self.key)

    def encrypt(self,nonce,plaintext,associated_data):
        return self.aes.encrypt(nonce,plaintext,associated_data)
    
    def decrypt(self,nonce,ciphertext,associated_data):
        return self.aes.decrypt(nonce,ciphertext,associated_data)
    