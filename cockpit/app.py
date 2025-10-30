import streamlit as st
from streamlit_webrtc import webrtc_streamer, WebRtcMode

st.set_page_config(page_title="Fusion Cockpit", layout="wide")

st.title("Fusion Cockpit")

st.sidebar.header("配置")
use_multi_gpu = st.sidebar.checkbox("启用双GPU并行", value=True)
input_type = st.sidebar.selectbox("输入源", ["webrtc_client", "local_cam", "rtsp"])
cam_id = st.sidebar.number_input("本地摄像头ID", value=0, step=1)
rtsp_url = st.sidebar.text_input("RTSP URL", value="")

st.sidebar.header("资产上传")
face_file = st.sidebar.file_uploader("上传源人脸", type=["jpg", "png", "jpeg"])
bg_file = st.sidebar.file_uploader("上传背景（图片或视频）", type=["jpg", "png", "jpeg", "mp4", "mov"])

backend = st.text_input("后端地址", value="http://localhost:8000")

if face_file is not None:
    import requests
    r = requests.post(f"{backend}/files/upload/face", files={"file": (face_file.name, face_file.getvalue())})
    st.success(r.json())

if bg_file is not None:
    import requests
    r = requests.post(f"{backend}/files/upload/background", files={"file": (bg_file.name, bg_file.getvalue())})
    st.success(r.json())

col1, col2 = st.columns(2)

with col1:
    if st.button("启动流水线"):
        import requests
        body = {
            "use_multi_gpu": use_multi_gpu,
            "input_source": {
                "type": input_type,
                "id": cam_id,
                "url": rtsp_url,
            },
        }
        r = requests.post(f"{backend}/stream/start", json=body)
        st.write(r.status_code, r.text)

with col2:
    if st.button("停止流水线"):
        import requests
        r = requests.post(f"{backend}/stream/stop")
        st.write(r.status_code, r.text)

st.subheader("WebRTC 预览（前端采集或后端输出对接待实现）")
webrtc_streamer(key="sendonly", mode=WebRtcMode.SENDONLY)