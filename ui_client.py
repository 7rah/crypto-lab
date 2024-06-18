import json
import os
import socket
import time
import streamlit as st

from config import CLIENT_STATE_DIR
from config import client_addr


uploading_files = []
uploaded_files = []

def update_file_status():
    global uploading_files, uploaded_files
    uploading_files = []
    uploaded_files = []
    for file in os.listdir(CLIENT_STATE_DIR):
        if file.startswith("finished_"):
            uploaded_files.append(file)
        else:
            uploading_files.append(file)

st.title("文件上传")




# 渲染单个已上传的文件状态
def render_uploaded_files(uploaded_file):
    with open(os.path.join(CLIENT_STATE_DIR, uploaded_file)) as f:
        try:
            state = json.load(f)
        except:
            return
    s = f"""
文件名：{state['file_name']}
```
存储路径：{state['file_path']}
文件大小：{state['file_size']/1024/1024}MB
文件哈希：{state['file_sha256']}
块大小：{state['block_size']/1024/1024:.2f}MB  块数量：{state['block_count']}  已上传块：{len(state['uploaded_blocks'])}
"""
    st.info(s)


def render_block_status(uploaded_blocks, block_count):
    # 控制每行显示的块数量
    LINE_DISPLAY_COUNT = 50
    uploaded_blocks = set(uploaded_blocks)

    # 计算块的相对位置，比如 uploaded_blocks = {1,2,3,5,6,10}，block_count = 15
    # 那么 block_status = [1,1,1,0,1,1,0,0,0,0,1,0,0,0,0]
    
    res = ""
    for i in range(block_count):
        if i in uploaded_blocks:
            res += "■"
        else:
            res += "□"
    
    # 每 LINE_DISPLAY_COUNT 个块换行，最终结果还是字符串
    res = [res[i:i+LINE_DISPLAY_COUNT] for i in range(0, len(res), LINE_DISPLAY_COUNT)]
    res = "\n".join(res)
    return res


# 渲染单个上传中的文件状态
def render_uploading_files(uploading_file):
    with open(os.path.join(CLIENT_STATE_DIR, uploading_file)) as f:
        try:
            state = json.load(f)
        except:
            return
    s = f"""
文件名：{state['file_name']}
```
存储路径：{state['file_path']}
文件大小：{state['file_size']/1024/1024}MB
文件哈希：{state['file_sha256']}
块大小：{state['block_size']/1024/1024:.2f}MB  块数量：{state['block_count']}  已上传块：{len(state['uploaded_blocks'])}


```
已上传块可视化 下载进度：{len(state['uploaded_blocks'])}/{state['block_count']}={len(state['uploaded_blocks'])/state['block_count']:.2%}
```
{render_block_status(state['uploaded_blocks'], state['block_count'])}
```
"""
    st.info(s)


PENDING_UPDATE_DIR = "pending_upload"

# 文件上传
uploaded_file = st.file_uploader("选择文件上传")
if uploaded_file is not None:
    file_name = uploaded_file.name
    file_path = os.path.join(PENDING_UPDATE_DIR, file_name)
    with open(file_path, 'wb') as f:
        f.write(uploaded_file.getvalue())
    
    st.write(f"文件 {file_name} 上传成功，下面把文件推送到 B 上")

    conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    conn.connect(client_addr)
    conn.send(file_path.encode())
    print(f"文件 {file_name} 上传成功，下面把文件推送到 B 上")



placeholder = st.empty()



while True:
    update_file_status()
    with placeholder.container():
        st.markdown("## 正在上传的文件")
        for file in uploading_files:
            render_uploading_files(file)
        st.markdown("---")
        st.markdown("## 已上传的文件")
        for file in uploaded_files:
            render_uploaded_files(file)

    time.sleep(0.1)