import time
from typing import Dict, Any

import cv2
import streamlit as st
try:
    from cockpit.ui_components import (
        build_sidebar_controls,
        render_gallery_selectors,
        render_header_with_logo,
        render_ui_config_editor,
    )
except Exception:
    import os, sys
    sys.path.append(os.path.dirname(__file__))
    from ui_components import (
        build_sidebar_controls,
        render_gallery_selectors,
        render_header_with_logo,
        render_ui_config_editor,
    )
from streamlit_webrtc import webrtc_streamer, WebRtcMode, VideoProcessorBase
import logging
import os

st.set_page_config(page_title="Fusion Cockpit", layout="wide")
# 统一日志器，确保在 Streamlit 环境下也能输出 DEBUG
logger = logging.getLogger("fusion.cockpit")
logger.setLevel(logging.DEBUG)
if not logger.handlers:
    _h = logging.StreamHandler()
    _h.setLevel(logging.DEBUG)
    _fmt = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    _h.setFormatter(_fmt)
    logger.addHandler(_h)

render_header_with_logo()

# 在侧栏提供“界面配置”编辑器（标题、Logo、背景图/开关），自动保存并即时应用
_ui_cfg = render_ui_config_editor(location="sidebar")

cfg = build_sidebar_controls()
use_multi_gpu = cfg["use_multi_gpu"]
input_type = cfg["input_type"]
cam_id = cfg["cam_id"]
rtsp_url = cfg["rtsp_url"]
res_label = cfg["res_label"]
fps_target = cfg["fps_target"]
facing_mode = cfg["facing_mode"]
enable_faceswap = cfg["enable_faceswap"]
raw_preview = cfg["raw_preview"]
process_every_n = cfg["process_every_n"]
local_direct_preview = cfg["local_direct_preview"]
W = cfg["W"]
H = cfg["H"]
bg_color = cfg["bg_color"]
backend = cfg["backend"]

st.sidebar.header("资产上传")
face_file = st.sidebar.file_uploader("上传源人脸", type=["jpg", "png", "jpeg"])
bg_file = st.sidebar.file_uploader("上传背景（图片或视频）", type=["jpg", "png", "jpeg", "mp4", "mov"])

if face_file is not None:
    import requests
    r = requests.post(f"{backend}/files/upload/face", files={"file": (face_file.name, face_file.getvalue())})
    st.success(r.json())

if bg_file is not None:
    import requests
    r = requests.post(f"{backend}/files/upload/background", files={"file": (bg_file.name, bg_file.getvalue())})
    st.success(r.json())

# 使用组件渲染画廊选择（替代内联实现）
gallery = render_gallery_selectors()

st.subheader("视频采集与实时统计")
st.subheader("日志输出")
log_area = st.empty()


class StatsProcessor(VideoProcessorBase):
    def __init__(self):
        self._last_ts = time.time()
        self._count = 0
        self.fps = 0.0
        # 处理帧统计
        self._proc_count = 0
        self.proc_fps = 0.0
        self.bitrate_kbps = 0.0
        self.frames_received = 0
        self.frames_displayed = 0
        self.last_proc_ms = 0.0
        # 日志打印节流
        self._last_log_ts = time.time()

    def recv(self, frame):
        t0 = time.time()
        now = time.time()
        self._count += 1
        self.frames_received += 1
        if now - self._last_ts >= 1.0:
            self.fps = self._count / (now - self._last_ts)
            # 计算处理帧FPS（在同一时间窗内）
            self.proc_fps = self._proc_count / max((now - self._last_ts), 1e-6)
            self._count = 0
            self._proc_count = 0
            self._last_ts = now
            # 终端每秒打印一次关键统计
            logger.debug(
                "[webrtc] recv_fps=%.1f proc_fps=%.1f recv=%d disp=%d proc_ms=%.2f kbps=%.1f",
                self.fps,
                self.proc_fps,
                self.frames_received,
                self.frames_displayed,
                self.last_proc_ms,
                self.bitrate_kbps,
            )

        # 原始直通或跳帧时尽量避免像素转换（从处理器属性读取，避免线程访问 Streamlit）
        raw = bool(getattr(self, "raw_preview", False))
        every_n = int(getattr(self, "process_every_n", 1))
        do_process = (self.frames_received % max(every_n, 1) == 0) and (not raw)

        if not do_process:
            # 直通返回，几乎零拷贝，显著降低CPU占用
            self.last_proc_ms = (time.time() - t0) * 1000.0
            self.frames_displayed += 1
            return frame

        img = frame.to_ndarray(format="bgr24")
        self._proc_count += 1
        cv2.putText(img, f"FPS: {self.fps:.1f}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
        cv2.putText(img, f"Net: {self.bitrate_kbps:.1f} kbps", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 200, 255), 2)
        import av
        out = av.VideoFrame.from_ndarray(img, format="bgr24")
        self.last_proc_ms = (time.time() - t0) * 1000.0
        self.frames_displayed += 1
        return out


def _poll_webrtc_stats_once(ctx, bitrate_placeholder, fps_placeholder, mode: WebRtcMode | None = None) -> None:
    prev_bytes_in = st.session_state.get("_prev_bytes_in", 0)
    prev_ts_in = st.session_state.get("_prev_ts_in", 0)
    prev_bytes_out = st.session_state.get("_prev_bytes_out", 0)
    prev_ts_out = st.session_state.get("_prev_ts_out", 0)
    try:
        reports: Dict[str, Any] = ctx.get_stats()
        inbound_video = [r for r in reports.values() if getattr(r, "type", "") == "inbound-rtp" and getattr(r, "kind", "") == "video"]
        outbound_video = [r for r in reports.values() if getattr(r, "type", "") == "outbound-rtp" and getattr(r, "kind", "") == "video"]

        # 下行速率（服务器->浏览器）
        total_bytes_in = sum(getattr(r, "bytesReceived", 0) for r in inbound_video)
        ts_in = max(getattr(r, "timestamp", 0) for r in inbound_video) if inbound_video else int(time.time() * 1000)
        delta_b_in = max(total_bytes_in - prev_bytes_in, 0)
        delta_t_in_ms = max(ts_in - prev_ts_in, 1)
        kbps_in = (delta_b_in * 8 / (delta_t_in_ms / 1000)) / 1000.0 if inbound_video else 0.0
        st.session_state["_prev_bytes_in"] = total_bytes_in
        st.session_state["_prev_ts_in"] = ts_in

        # 上行速率（浏览器->服务器）
        total_bytes_out = sum(getattr(r, "bytesSent", 0) for r in outbound_video)
        ts_out = max(getattr(r, "timestamp", 0) for r in outbound_video) if outbound_video else int(time.time() * 1000)
        delta_b_out = max(total_bytes_out - prev_bytes_out, 0)
        delta_t_out_ms = max(ts_out - prev_ts_out, 1)
        kbps_out = (delta_b_out * 8 / (delta_t_out_ms / 1000)) / 1000.0 if outbound_video else 0.0
        st.session_state["_prev_bytes_out"] = total_bytes_out
        st.session_state["_prev_ts_out"] = ts_out
        # 更新主线程指标与处理器内部比特率
        if getattr(ctx, "video_processor", None):
            try:
                # 处理器记录“当前展示链路”的速率：SENDONLY 用上行，SENDRECV 用下行
                if mode == WebRtcMode.SENDONLY:
                    ctx.video_processor.bitrate_kbps = kbps_out
                else:
                    ctx.video_processor.bitrate_kbps = kbps_in
            except Exception:
                pass
        # 根据模式选择展示速率
        if mode == WebRtcMode.SENDONLY:
            bitrate_placeholder.metric("上行速度", f"{kbps_out:.1f} kbps")
        else:
            bitrate_placeholder.metric("下行速度", f"{kbps_in:.1f} kbps")
        fps_val = 0.0
        if getattr(ctx, "video_processor", None):
            try:
                fps_val = ctx.video_processor.fps
                proc_fps_val = getattr(ctx.video_processor, "proc_fps", 0.0)
                # 刷新日志输出：接收帧/显示帧/处理时延
                fr = ctx.video_processor.frames_received
                fd = ctx.video_processor.frames_displayed
                lp = ctx.video_processor.last_proc_ms
                log_area.markdown(
                    f"- 模式: webrtc_client\n"
                    f"- 接收帧: `{fr}`\n"
                    f"- 显示帧: `{fd}`\n"
                    f"- 处理耗时: `{lp:.2f} ms/frame`\n"
                    f"- 接收FPS: `{fps_val:.1f}`\n"
                    f"- 处理FPS: `{proc_fps_val:.1f}`\n"
                    f"- 下行速率: `{kbps_in:.1f} kbps`\n"
                    f"- 上行速率: `{kbps_out:.1f} kbps`\n"
                )
            except Exception:
                pass
        fps_placeholder.metric("帧率", f"{fps_val:.1f} fps")
    except Exception:
        # 安全降级：若统计不可用，则保持现有值
        pass


# 采集源选择与预览
preview_container = st.container()
with preview_container:
    if input_type == "webrtc_client":
        st.info("浏览器摄像头采集（WebRTC）")
        # 日志刷新开关
        log_refresh = st.sidebar.checkbox("持续刷新日志", value=True)
        # 根据选择构建视频约束
        # 放宽采集约束，提升浏览器兼容性（某些设备在严格 max FPS 下不返回流）
        video_constraints = {
            "width": {"ideal": W, "max": W},
            "height": {"ideal": H, "max": H},
            # 仅提供 ideal，避免硬限制导致 getUserMedia 失败
            "frameRate": {"ideal": fps_target},
            # 明确请求硬件加速可用的标准编码（由浏览器端自动选择硬件路径）
            # 注意：编码器选择由浏览器控制，服务器无法强制，但 webrtc 通常优先硬件 H.264/VP8
        }
        if facing_mode != "auto":
            video_constraints["facingMode"] = facing_mode

        # 本地直显：纯浏览器直显；常规：双向
        webrtc_mode = WebRtcMode.SENDRECV

        kwargs = dict(
            key="webrtc-client",
            mode=webrtc_mode,
            media_stream_constraints={
                "video": video_constraints,
                "audio": False,
            },
            rtc_configuration={
                "iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}],
            },
            async_processing=True,
            video_html_attrs={
                "style": {"width": "100%", "height": "auto", "max-height": "70vh", "border": "1px solid #ddd", "backgroundColor": "#000"},
                # 打开 controls 便于用户点击播放/静音，绕过部分移动端自动播放限制
                "controls": True,
                "autoPlay": True,
                "muted": True,
                "playsInline": True,
            },
        )
        # 本地直显：不创建 webrtc 组件，使用纯浏览器预览并提供 START/STOP
        if local_direct_preview:
            import streamlit.components.v1 as components
            try:
                from cockpit.grid_ui import render_local_2x3_grid as _render_grid
            except Exception:
                import os, sys
                sys.path.append(os.path.dirname(__file__))
                from grid_ui import render_local_2x3_grid as _render_grid
            enabled = bool(st.session_state.get("local_preview_enabled", False))
            label = "STOP" if enabled else "START"
            btn_type = "primary" if enabled else "secondary"
            if st.button(label, type=btn_type, use_container_width=True, key="startstop_toggle"):
                st.session_state["local_preview_enabled"] = not enabled
                enabled = not enabled

            fm = f'"{facing_mode}"' if facing_mode != "auto" else 'undefined'
            html = f"""
            <div id=\"wrap\" style=\"position:relative;width:100%;max-height:70vh;border:1px solid #ddd;background:#000;overflow:hidden\">
              <video id=\"localPreview\" autoplay muted playsinline style=\"width:100%;height:auto;display:block\"></video>
              <div id=\"centerLabel\" style=\"position:absolute;left:50%;top:50%;transform:translate(-50%,-50%);color:#fff;font:600 18px/1.6 sans-serif;background:rgba(0,0,0,.35);padding:6px 10px;border-radius:6px\">原始摄像头采集</div>
              <div id=\"hud\" style=\"position:absolute;left:8px;top:8px;color:#0f0;background:rgba(0,0,0,.4);padding:4px 6px;border-radius:4px;font:14px/1.4 monospace\">帧: 0 | FPS: 0.0</div>
            </div>
            <script>
            (function() {{
              const enabled = {str(enabled).lower()};
              const width = {W};
              const height = {H};
              const fpsIdeal = {fps_target};
              const facing = {fm};
              const constraints = {{
                video: {{ width: {{ ideal: width, max: width }}, height: {{ ideal: height, max: height }}, frameRate: {{ ideal: fpsIdeal }}, facingMode: facing }},
                audio: false
              }};
              const v = document.getElementById('localPreview');
              const hud = document.getElementById('hud');
              let stream = v.srcObject || null;
              let frames = 0, lastT = performance.now(), fps = 0;

              function stopStream() {{
                if (stream) {{
                  stream.getTracks().forEach(t => t.stop());
                  stream = null; v.srcObject = null;
                }}
              }}
              async function startStream() {{
                try {{
                  stream = await navigator.mediaDevices.getUserMedia(constraints);
                  v.srcObject = stream;
                  frames = 0; lastT = performance.now(); fps = 0;
                  if ('requestVideoFrameCallback' in v) {{
                    const cb = (now, meta) => {{
                      frames++;
                      const dt = now - lastT;
                      if (dt >= 1000) {{ fps = (frames * 1000) / dt; frames = 0; lastT = now; }}
            hud.textContent = '帧: ' + frames + ' | FPS: ' + fps.toFixed(1);
                      v.requestVideoFrameCallback(cb);
                    }};
                    v.requestVideoFrameCallback(cb);
                  }} else {{
                    // 兼容 FRC 不可用的环境
                    setInterval(() => {{ hud.textContent = `FPS 估计中...`; }}, 1000);
                  }}
                }} catch (e) {{
                  hud.textContent = '无法打开摄像头: ' + e.message;
                }}
              }}
              if (enabled) startStream(); else stopStream();
            }})();
            </script>
            """
            _render_grid(
                enabled=enabled,
                W=W,
                H=H,
                fps_target=fps_target,
                facing_mode=facing_mode,
                bg_color=bg_color,
            )

            st.caption("提示：如自动播放受限，请点击视频上的播放按钮或检查浏览器摄像头权限。")
        else:
            # 使用新API：video_processor_factory + recv()
            kwargs["video_processor_factory"] = StatsProcessor
            webrtc_ctx = webrtc_streamer(**kwargs)
        if not local_direct_preview and webrtc_ctx.state.playing:
            bitrate_ph = st.empty()
            fps_ph = st.empty()
            # 本地直接显示模式：纯浏览器直显，不经服务器编码回传
            if local_direct_preview:
                st.session_state["log_lines"] = [
                    "✅ 本地直接显示：浏览器直接播放摄像头（GPU渲染），服务器不回传",
                    "ℹ️ 若仍无画面：点击视频播放、检查权限、或尝试更换浏览器",
                ]
                st.success("本地直接显示已启用：不回传、最低延迟、最低CPU占用")
                st.caption("WebRTC 已启动：若未显示视频，请在浏览器允许摄像头权限。")
            else:
                # 在主线程将当前配置下发到处理器，避免线程中访问 Streamlit API
                if getattr(webrtc_ctx, "video_processor", None):
                    try:
                        webrtc_ctx.video_processor.raw_preview = bool(st.session_state.get("raw_preview", False))
                        webrtc_ctx.video_processor.process_every_n = int(st.session_state.get("process_every_n", 1))
                    except Exception:
                        pass
                # 单次刷新或持续刷新日志
                if log_refresh:
                    # 控制刷新时长，避免阻塞页面过久
                    start_poll = time.time()
                    while webrtc_ctx.state.playing and (time.time() - start_poll < 180):  # 最多刷180秒
                        _poll_webrtc_stats_once(webrtc_ctx, bitrate_ph, fps_ph, mode=webrtc_mode)
                        time.sleep(1.0)
                else:
                    _poll_webrtc_stats_once(webrtc_ctx, bitrate_ph, fps_ph, mode=webrtc_mode)
                st.caption("WebRTC 已启动：若未显示视频，请在浏览器允许摄像头权限。")
        elif not local_direct_preview:
            st.warning("WebRTC 未连接：请点击上方组件并允许摄像头访问。")
    elif input_type == "local_cam":
        st.info("本地摄像头采集（服务器侧）")
        has_local_cam = os.path.exists("/dev/video0")
        if not has_local_cam:
            st.warning("服务器未检测到 /dev/video0，本地摄像头选项已隐藏；请稍后处理本地摄像头问题。")
            st.stop()
        frame_placeholder = st.empty()
        fps_placeholder = st.empty()
        net_placeholder = st.empty()
        try:
            cap = cv2.VideoCapture(int(cam_id))
            # 应用分辨率设置，实际支持取决于驱动
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, W)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, H)
            cap.set(cv2.CAP_PROP_FPS, fps_target)
            if not cap.isOpened():
                st.error(f"无法打开本地摄像头 ID={cam_id}")
            else:
                start_ts = time.time()
                frames = 0
                # 预览 10 秒以避免阻塞页面
                while time.time() - start_ts < 10:
                    ret, frame = cap.read()
                    if not ret:
                        st.error("摄像头读取失败")
                        break
                    frames += 1
                    fps = frames / max(time.time() - start_ts, 1e-6)
                    cv2.putText(frame, f"FPS: {fps:.1f}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
                    cv2.putText(frame, "Net: 本地采集", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 200, 255), 2)
                    frame_placeholder.image(frame, channels="BGR")
                    fps_placeholder.metric("帧率", f"{fps:.1f} fps")
                    net_placeholder.metric("网络速度", "N/A")
                    time.sleep(max(1 / float(fps_target), 1/60))
        finally:
            try:
                cap.release()
            except Exception:
                pass
    else:
        st.info("RTSP 预览尚未接入（需后端WebRTC输出）")