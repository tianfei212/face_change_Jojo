import os
import base64
import streamlit as st
from typing import Dict, Any, List

# 读写前端配置（容错导入）
try:
    from cockpit.frontend_config import load_config, save_config
except Exception:
    import sys
    sys.path.append(os.path.dirname(__file__))
    from frontend_config import load_config, save_config  # type: ignore


def _file_to_data_url(path: str) -> str:
    try:
        with open(path, "rb") as f:
            data = base64.b64encode(f.read()).decode("utf-8")
        ext = os.path.splitext(path)[1].lower().strip(".") or "png"
        return f"data:image/{ext};base64,{data}"
    except Exception:
        return ""


def apply_page_background(image_path: str | None = None) -> None:
    url = _file_to_data_url(image_path) if (image_path and os.path.exists(image_path)) else ""
    if not url:
        # 渐变背景作为兜底
        css = """
        <style>
        .stApp { background: linear-gradient(135deg, #0f0f10 0%, #1a1c1f 60%, #111215 100%); }
        </style>
        """
        st.markdown(css, unsafe_allow_html=True)
        return
    css = f"""
    <style>
    .stApp {{ background-image: url('{url}'); background-size: cover; background-attachment: fixed; }}
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)


def render_header_with_logo() -> None:
    cfg = load_config()
    title = cfg.get("title", "Fusion Cockpit")
    logo_path = cfg.get("logo_path", "assets/user/logo.png")
    bg_enabled = bool(cfg.get("background_enabled", False))
    bg_path = cfg.get("background_path", "assets/user/bg.jpg")

    left, mid, right = st.columns([1, 6, 1])
    with left:
        if os.path.exists(logo_path):
            st.image(logo_path, caption=None, use_container_width=True)
        else:
            st.markdown("<div style='font-weight:700;font-size:18px'>Fusion</div>", unsafe_allow_html=True)
    with mid:
        st.title(title)
    with right:
        # 为满足“仅通过配置文件控制”，不再提供界面切换按钮
        pass

    if bg_enabled:
        apply_page_background(bg_path)
    else:
        apply_page_background(None)


def _list_files(patterns: List[str]) -> List[str]:
    import glob
    files: List[str] = []
    for p in patterns:
        files.extend(glob.glob(p))
    return sorted(files)


def _image_candidates() -> List[str]:
    return _list_files([
        os.path.join("assets", "user", "*.png"),
        os.path.join("assets", "user", "*.jpg"),
        os.path.join("assets", "user", "*.jpeg"),
        os.path.join("assets", "user", "*.webp"),
        os.path.join("assets", "user", "*.gif"),
    ])


def render_gallery_selectors() -> Dict[str, Any]:
    st.markdown("---")
    st.subheader("画廊模式选择")
    face_candidates = _list_files([
        os.path.join("assets", "user", "*.jpg"),
        os.path.join("assets", "user", "*.jpeg"),
        os.path.join("assets", "user", "*.png"),
    ])
    bg_candidates = _list_files([
        os.path.join("assets", "user", "*.jpg"),
        os.path.join("assets", "user", "*.jpeg"),
        os.path.join("assets", "user", "*.png"),
        os.path.join("assets", "user", "*.mp4"),
        os.path.join("assets", "user", "*.mov"),
    ])
    col_g1, col_g2 = st.columns(2)
    with col_g1:
        dfm_sel = st.selectbox(
            "脸图（DFM）模型",
            options=(face_candidates if face_candidates else ["（无可用，先在侧边栏上传人脸）"]),
            index=0,
            key="dfm_select",
        )
    with col_g2:
        bg_sel = st.selectbox(
            "背景图/视频",
            options=(bg_candidates if bg_candidates else ["（无可用，先在侧边栏上传背景）"]),
            index=0,
            key="bg_select",
        )
    st.session_state["dfm_model_path"] = dfm_sel
    st.session_state["bg_source_path"] = bg_sel
    st.caption("提示：可在左侧“资产上传”中上传人脸与背景文件，随后在此选择。")
    st.markdown("---")
    return {"dfm_model_path": dfm_sel, "bg_source_path": bg_sel}


def render_ui_config_editor(location: str = "sidebar") -> Dict[str, Any]:
    """为兼容旧调用保留空实现：根据需求，界面不再提供这些配置项。
    仅返回当前配置的快照，且不渲染任何输入控件。
    """
    return load_config()


def render_obs_controls() -> Dict[str, Any]:
    """侧栏：OBS 输出配置与全屏窗口按钮（持久化到 cockpit/ui_config.json）。"""
    # 直接使用文件顶部已导入的 load_config/save_config，避免相对导入导致包上下文问题
    cfg = load_config()
    st.sidebar.header("OBS 输出")
    obs_enabled_def = bool(cfg.get("obs_enabled", False))
    obs_choice = st.sidebar.radio(
        "输出到 OBS（HTTP）",
        options=["关闭", "开启"],
        index=(1 if obs_enabled_def else 0),
        horizontal=True,
    )
    obs_enabled = (obs_choice == "开启")
    obs_url = st.sidebar.text_input("OBS 地址", value=str(cfg.get("obs_url", "http://localhost:8000/obs/push")))

    if obs_enabled != obs_enabled_def or obs_url != cfg.get("obs_url"):
        cfg["obs_enabled"] = obs_enabled
        cfg["obs_url"] = obs_url
        save_config(cfg)
        st.sidebar.caption("OBS 配置已保存")

    # 打开新窗口以满屏显示最终融合画面（使用 query 参数 fullscreen=1）
    open_full_btn = st.sidebar.button("打开满屏输出窗口", use_container_width=True)
    if open_full_btn:
        import streamlit.components.v1 as components
        components.html(
            """
            <script>
              const url = new URL(window.location.href);
              url.searchParams.set('fullscreen', '1');
              window.open(url.toString(), '_blank');
            </script>
            """,
            height=0,
        )

    st.session_state["obs_enabled"] = obs_enabled
    st.session_state["obs_url"] = obs_url
    return {"obs_enabled": obs_enabled, "obs_url": obs_url}


def build_sidebar_controls() -> Dict[str, Any]:
    st.sidebar.header("配置")
    use_multi_gpu = st.sidebar.checkbox("启用双GPU并行", value=True)

    # 输入源选择，始终提供本地摄像头项
    has_local_cam = os.path.exists("/dev/video0")
    input_options = ["webrtc_client", "local_cam", "rtsp"]
    input_type = st.sidebar.selectbox("输入源", input_options, index=0)

    cam_id = None
    rtsp_url = None
    if input_type == "local_cam":
        cam_id = st.sidebar.number_input("本地摄像头ID", value=0, step=1)
        if not has_local_cam:
            st.sidebar.warning("服务器未检测到 /dev/video0，尝试前请检查设备。")
    elif input_type == "rtsp":
        rtsp_url = st.sidebar.text_input("RTSP URL", value="")

    # 采集参数
    st.sidebar.header("采集参数")
    res_label = st.sidebar.selectbox("分辨率", ["360p", "480p", "720p", "2k"], index=1)
    fps_target = st.sidebar.slider("帧率 (FPS)", min_value=10, max_value=60, value=24, step=2)
    facing_mode = st.sidebar.selectbox("摄像头方向", ["auto", "user", "environment"], index=0)

    # 语义改为“开启换脸”
    enable_faceswap = st.sidebar.checkbox("开启换脸", value=False)
    raw_preview = not enable_faceswap
    process_every_n = st.sidebar.slider("每N帧处理一次", min_value=1, max_value=5, value=2)
    local_direct_preview = st.sidebar.checkbox("本地直接显示（不回传）", value=True)
    RESOLUTION_MAP = {"360p": (640, 360), "480p": (640, 480), "720p": (1280, 720), "2k": (2560, 1440)}
    W, H = RESOLUTION_MAP.get(res_label, (640, 480))

    # 显示设置与后端地址（移动到左侧）
    st.sidebar.header("显示设置")
    bg_color = st.sidebar.color_picker("纯色背景颜色", value="#000000")
    backend = st.sidebar.text_input("后端地址", value="http://localhost:8000")

    # 同步会话状态供处理器读取
    st.session_state["raw_preview"] = raw_preview
    st.session_state["process_every_n"] = process_every_n
    if "local_preview_enabled" not in st.session_state:
        st.session_state["local_preview_enabled"] = False

    return dict(
        use_multi_gpu=use_multi_gpu,
        input_type=input_type,
        cam_id=cam_id if cam_id is not None else 0,
        rtsp_url=rtsp_url or "",
        res_label=res_label,
        fps_target=fps_target,
        facing_mode=facing_mode,
        enable_faceswap=enable_faceswap,
        raw_preview=raw_preview,
        process_every_n=process_every_n,
        local_direct_preview=local_direct_preview,
        W=W,
        H=H,
        bg_color=bg_color,
        backend=backend,
    )