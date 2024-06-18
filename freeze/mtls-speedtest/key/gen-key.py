
import rsa

# 定义生成密钥的函数
def gen_key(pub_path, pri_path):
    # 生成密钥，并保存在文件中
    (pubkey, privkey) = rsa.newkeys(2048)
    pub = pubkey.save_pkcs1()
    pri = privkey.save_pkcs1()
    with open(pub_path, 'wb') as f:
        f.write(pub)
    with open(pri_path, 'wb') as f:
        f.write(pri)

gen_key('A_pub.pem', 'A_pri.pem')
gen_key('B_pub.pem', 'B_pri.pem')