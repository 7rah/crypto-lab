
import hashlib
import json
import os
import time
import zstd
from config import *


# 计算文件 SHA-256 
def calc_file_sha256(file_path):
    with open(file_path, 'rb') as f:
        sha256 = hashlib.sha256()
        while True:
            data = f.read(16384)
            if not data:
                break
            sha256.update(data)
        return sha256.hexdigest()


class UploadClient:
    def __init__(self, file_path,io):
        self.io = io

        # 读取文件，获取文件名
        self.file_name = os.path.basename(file_path)
        # 转为绝对路径
        self.file_path = os.path.abspath(file_path)

        # 打开文件
        self.file = open(self.file_path, 'rb')

        # 如果文件不存在，新建一个，并记录状态
        # 状态包括，文件名，文件大小，已上传的块，未上传的块，块大小，块数量，文件哈希
        
        file_sha256 = calc_file_sha256(self.file_path)
        state_json_name = f"{file_sha256[:8]}_{self.file_name}.json"

        state_json_path = os.path.join(CLIENT_STATE_DIR, state_json_name)

        self.state = {}
        if os.path.exists(state_json_path):
            with open(state_json_path, 'r') as f:
                self.state = json.load(f)
        else:
            # metadata
            self.state["state_json_name"] = state_json_name
            self.state["file_name"] = self.file_name
            self.state["file_path"] = self.file_path
            self.state["file_size"] = os.path.getsize(self.file_path)
            self.state["file_sha256"] = file_sha256

            # state
            self.state["block_size"] = DEFALUT_BLOCK_SIZE
            # 向上取整
            self.state["block_count"] = (self.state["file_size"] + self.state["block_size"] - 1) // self.state["block_size"]
            self.state["uploaded_blocks"] = []

            # 格式化保存，要空行
            with open(state_json_path, 'w') as f:
                json.dump(self.state, f, indent=4)

    # 握手
    # C  -> S: 文件元数据
    # S  -> C: ok
    def handshake(self):
        # 向服务器发送文件元数据
        send_state = self.state.copy()
        send_state.pop("file_path")

        # 以 utf-8 格式 json 化，最后编码为 bytes
        data = json.dumps(send_state).encode('utf-8')
        # 发送文件元数据
        self.io.send(data)

        # 读取服务器返回的状态
        data = self.io.recv()
        # 解码为 utf-8 格式，然后 json 化
        recv_state = json.loads(data.decode('utf-8'))
        if recv_state["status"] != "ok":
            raise Exception("握手失败")
        
        print("文件发送：握手成功")

    
    def get_single_block(self,block_index):
        self.file.seek(block_index * self.state["block_size"])
        # 如果不是最后一个块
        if block_index != self.state["block_count"] - 1:
            block_data = self.file.read(self.state["block_size"])
        else:
            block_data = self.file.read(self.state["file_size"] % self.state["block_size"])

        # 计算 sha256
        sha256 = hashlib.sha256(block_data).digest()

        if ENABLE_COMPRESSION:
            compressed_block_data = zstd.compress(block_data)
            if len(compressed_block_data) < self.state["block_size"]:
                return (True,sha256,compressed_block_data)
            
        return (False,sha256,block_data)

        
    
    # 发送单个块
    # C  -> S: 块编号，块数据
    # S  -> C: state

    # 格式
    # | type(1)        | # 发送的数据包有无压缩
    # | block_index(8) |
    # | sha256(32)     | # 这里的 sha256 永远是未压缩的数据的 sha256
    # | block_data     |

    def send_single_block(self,block_index):
        time_prev = time.time()

        is_compress,sha256,block_data = self.get_single_block(block_index)

        # 发送数据包
        block_type = 1 if is_compress else 0
        block_type = block_type.to_bytes(1,byteorder='big')
        block_index_send = block_index.to_bytes(8,byteorder='big')
        
        data = block_type + block_index_send + sha256 + block_data

        self.io.send(data)


        # 计算速度
        time_now = time.time()
        speed = len(block_data) / (time_now - time_prev) / 1024 / 1024
        uploaded_count = len(self.state["uploaded_blocks"])
        print(f"文件发送：发送块:{block_index} 压缩状态:{int(is_compress)} 速度:{speed:.4} MB/s 进度:{uploaded_count}/{self.state['block_count']}={uploaded_count/self.state['block_count']:.2%}")
    
    # 服务器返回格式
    # | block_index(8) |
    # | state(1)       | # 0: 未上传，1: 已上传
    def recv_state(self):
        data = self.io.recv()
        block_index = int.from_bytes(data[:8],byteorder='big')
        state = int.from_bytes(data[8:9],byteorder='big')

        return block_index,state
    
    # 发送文件
    def send_file(self):
        # 未上传的块
        unuploaded_blocks = set(range(self.state["block_count"])) - set(self.state["uploaded_blocks"])
        print("文件发送：开始发送")
        print(f"文件发送：未上传块 {unuploaded_blocks}")
        time_prev = time.time()
        for block_index in unuploaded_blocks:
            self.send_single_block(block_index)
            block_index,state = self.recv_state()
            if state == 1:
                if block_index not in self.state["uploaded_blocks"]:
                    self.state["uploaded_blocks"].append(block_index)
                    with open(os.path.join(CLIENT_STATE_DIR, self.state["state_json_name"]), 'w') as f:
                        json.dump(self.state, f, indent=4)
                        f.flush()

        print("文件发送：发送完成")

        # 重命名状态文件为 finished_
        os.rename(os.path.join(CLIENT_STATE_DIR, self.state["state_json_name"]), os.path.join(CLIENT_STATE_DIR, f"finished_{self.state['state_json_name']}"))


        

class UploadServer:
    def __init__(self,io):
        self.io = io


    # C  -> S: 文件元数据
    # S  -> C: ok
    def handshake(self):
        # 读取客户端发送的文件元数据
        data = self.io.recv()
        # 解码为 utf-8 格式，然后 json 化
        recv_state = json.loads(data.decode('utf-8'))

        # 检查文件是否存在
        file_path = os.path.join(SERVER_STATE_DIR, recv_state["state_json_name"])

        # 如果文件不存在，新建一个，并保存 recv_state
        if not os.path.exists(file_path):
            with open(file_path, 'w') as f:
                json.dump(recv_state, f, indent=4)

            # 新建文件并写入 0
            with open(os.path.join(SERVER_SAVE_FILE_DIR, recv_state["file_name"]), 'wb') as f:
                f.write(b'\x00' * recv_state["file_size"])

        else:
            with open(file_path, 'r') as f:
                recv_state = json.load(f)

        self.state = recv_state
        
        # 返回状态
        data = json.dumps({"status": "ok"}).encode('utf-8')
        self.io.send(data)

        print("文件接收：握手成功")
    
    # 格式
    # | type(1)        | # 发送的数据包有无压缩
    # | block_index(8) |
    # | sha256(32)     | # 这里的 sha256 永远是未压缩的数据的 sha256
    # | block_data     |
    def recv_single_block(self):
        time_prev = time.time()
        data = self.io.recv()
        block_type = int.from_bytes(data[:1],byteorder='big')
        block_index = int.from_bytes(data[1:9],byteorder='big')
        sha256 = data[9:41]
        block_data = data[41:]

        if block_type == 1:
            block_data = zstd.decompress(block_data)
        
        # 计算 sha256
        sha256_check = hashlib.sha256(block_data).digest()
        if sha256 != sha256_check:
            raise Exception("sha256 不匹配")
        
        
        # 计算速度
        time_now = time.time()
        speed = len(block_data) / (time_now - time_prev) / 1024 / 1024

        uploaded_count = len(self.state["uploaded_blocks"])
        print(f"文件接收：接收块:{block_index} 压缩状态:{int(block_type)} 速度:{speed:.4} MB/s 进度:{uploaded_count}/{self.state['block_count']}={uploaded_count/self.state['block_count']:.2%}")
        
        return block_index,block_data
    
    def send_state(self,block_index,state):
        block_index = block_index.to_bytes(8,byteorder='big')
        state = state.to_bytes(1,byteorder='big')
        data = block_index + state
        self.io.send(data)

    def recv_file(self):
        if len(self.state["uploaded_blocks"]) == self.state["block_count"]:
            return

        while True:
            try:
                block_index,block_data = self.recv_single_block()
                
                # 写入块，要计算块的偏移量
                with open(os.path.join(SERVER_SAVE_FILE_DIR, self.state["file_name"]), 'rb+') as f:
                    f.seek(block_index * self.state["block_size"])
                    f.write(block_data)
                    f.flush()
                
                self.send_state(block_index,1)

                # 保存状态文件
                if block_index not in self.state["uploaded_blocks"]:
                    self.state["uploaded_blocks"].append(block_index)

                with open(os.path.join(SERVER_STATE_DIR, self.state["state_json_name"]), 'w') as f:
                    json.dump(self.state, f, indent=4)
                    f.flush()

                if self.state["block_count"]  == len(self.state["uploaded_blocks"]):
                    print("已经接收完所有块，稍后计算文件哈希，可能需要一段时间")
                    break
            except Exception as e:
                print(e)
                break
        
        if len(self.state["uploaded_blocks"]) == self.state["block_count"]:
            sha256 = calc_file_sha256(os.path.join(SERVER_SAVE_FILE_DIR, self.state["file_name"]))
            print(f"文件接收：接收完成 {self.state['file_name']}")
            print("文件接收：收到的文件哈希",calc_file_sha256(os.path.join(SERVER_SAVE_FILE_DIR, self.state["file_name"])))

            print("文件接收：客户端发送过来的文件哈希",self.state["file_sha256"])
            if sha256 == self.state["file_sha256"]:
                print("文件接收：文件哈希匹配")
            else:
                print("文件接收：文件哈希不匹配")

            # 重命名状态文件为 finished_
            os.rename(os.path.join(SERVER_STATE_DIR, self.state["state_json_name"]), os.path.join(SERVER_STATE_DIR, f"finished_{self.state['state_json_name']}"))




        



        

