# B 作为服务器端，设定监听地址
server_addr = ('127.0.0.1', 9000)

# A 作为客户端，UI 连接地址
client_addr = ('127.0.0.1', 13000)

# 文件传输相关参数

# 默认分块大小
DEFALUT_BLOCK_SIZE = 5 * 1024 * 1024 # 5MB 

CLIENT_STATE_DIR = "client_state"
SERVER_STATE_DIR = "server_state"
SERVER_SAVE_FILE_DIR = "recv_file"
ENABLE_COMPRESSION = True

# mTLS 安全相关

# 允许的最大时间差，单位为秒
TIME_DIFF = 10