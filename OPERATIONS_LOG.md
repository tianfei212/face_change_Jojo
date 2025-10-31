# 操作记录（Operations Log）

记录在本项目中我执行的每一步操作、命令与变更，便于审计与复现。后续所有操作将持续追加到本文件。

## 概览
- 操作目标：按系统架构规划搭建后端 FastAPI 与前端 Streamlit 骨架，实现基础端点、依赖与运行环境；同步到 GitHub 并提供可预览的服务。
- 环境：`linux`，Python 3.12，虚拟环境路径 `./.venv`。

## 初始化与项目骨架
- 创建后端应用包与入口：
  - 新增 `app/__init__.py`、`app/main.py`（注册 CORS、全局状态、路由与启动事件）。
- 添加配置与工具：
  - 新增 `app/config.py`（模型URL占位、模型目录配置）。
  - 新增 `app/utils.py`（`ensure_dir` 与 `download_models`，含进度日志）。
- 注册启动事件：
  - 新增 `app/events.py`，在 `@app.on_event("startup")` 自动下载模型并设置 `models_ready`。
- 路由与端点：
  - 新增 `app/routers/system.py`（`GET /system/status`）。
  - 新增 `app/routers/files.py`（`POST /files/upload/face` 与 `POST /files/upload/background`）。
  - 新增 `app/routers/stream.py`（`POST /stream/start`、`POST /stream/stop`、`GET /stream/status`）。
  - 新增 `app/routers/webrtc.py`（`POST /webrtc/sdp` 占位）。
- 处理管理器与AI模块骨架：
  - 新增 `app/processing/manager.py`（队列、线程骨架与阶段串联）。
  - 新增 AI 模块骨架：`app/ai/face_detection.py`、`human_matting.py`、`face_parsing.py`、`face_swap.py`、`blending.py`、`composition.py`。
- 运行脚本与依赖：
  - 新增 `run.py`（`uvicorn` 启动后端）。
  - 新增 `requirements.txt`（后端与前端依赖清单）。
- 前端 Cockpit：
  - 新增 `cockpit/app.py`（上传资产、配置输入源、启动/停止流水线、WebRTC 预览占位）。

## 端点与用法修正
- 修正 FastAPI 端点使用 `Request` 访问应用状态：
  - 更新 `app/routers/system.py` 与 `app/routers/stream.py`，避免错误的参数注入。
- 简化上传端点参数：
  - 更新 `app/routers/files.py`，移除无效的 `app` 注入参数。

## 文档
- 新增 `README.md`（项目结构、依赖安装、运行说明、端点摘要、后续工作）。

## Git 同步到 GitHub
- 初始化本地仓库并首提交：
  - 运行：
    - `git init`
    - `git config user.name "Fusion"`
    - `git config user.email "fusion@example.local"`
    - `git add . && git commit -m "chore: initialize project skeleton"`
- 设定主分支与远程（首次尝试SSH失败）：
  - 运行：
    - `git branch -M main`
    - `git remote add origin git@github.com:tianfei212/face_change_Jojo.git`
    - `git tag -a v1.1.0 -m "Release 1.1.0"`
    - `git push -u origin main && git push origin v1.1.0`
  - 结果：SSH 推送失败（`Permission denied (publickey)`）。
- 生成并加载 SSH 密钥以便你添加到 GitHub：
  - 运行：
    - `ssh-keygen -t ed25519 -C "fusion@example.local" -f ~/.ssh/id_ed25519 -N ""`
    - 启动代理并添加：`eval "$(ssh-agent -s)" && ssh-add ~/.ssh/id_ed25519`
    - 输出公钥以便添加到 GitHub：`cat ~/.ssh/id_ed25519.pub`
- 切换至 HTTPS 远程并推送成功：
  - 运行：
    - `git remote set-url origin https://github.com/tianfei212/face_change_Jojo.git`
    - `git branch -M main`
    - `git push -u origin main`
    - `git push origin v1.1.0`
  - 结果：成功推送主分支与标签。

## 虚拟环境与依赖安装
- 创建虚拟环境首次失败（缺少 `ensurepip` / `python3-venv`）：
  - 输出：提示安装 `python3.12-venv`。
- 安装系统级依赖并创建虚拟环境：
  - 运行：
    - `sudo apt update && sudo apt install -y python3-venv python3-pip`
    - `python3 -m venv .venv`
    - `.venv/bin/pip install -U pip setuptools wheel`
    - `.venv/bin/pip install -r requirements.txt`
  - 结果：成功安装所有依赖（包括 `onnxruntime-gpu` 与 `av` 等）。

## 后端启动与路径修复
- 启动后端首次失败：
  - 运行：`.venv/bin/python run.py`
  - 错误：`PermissionError: [Errno 13] Permission denied: '/opt/fusion_assets'`
- 路径修复（迁移到项目内可写目录）：
  - 更新 `app/config.py`：将模型目录设为 `assets/models`。
  - 更新 `app/routers/files.py`：用户资产目录改为 `assets/user/...`。
  - 更新 `app/utils.py`：确保 `assets/` 与 `assets/models/` 自动创建。
- 安装缺失依赖并重启后端：
  - 运行：`.venv/bin/pip install python-multipart`
  - 重启：`.venv/bin/python run.py`
  - 结果：后端启动成功，监听 `http://0.0.0.0:8000`。
  - 预览：`http://localhost:8000/`

## 前端启动
- 启动 Streamlit Cockpit：
  - 运行：`.venv/bin/streamlit run cockpit/app.py`
  - 结果：前端启动成功。
  - 本地预览：`http://localhost:8502`

## 当前服务状态
- 后端：运行中，地址 `http://localhost:8000/`。
- 前端：运行中，地址 `http://localhost:8502/`。

## 后续计划（将追加日志）
- 接入真实模型下载与加载（RetinaFace/RVM/BiSeNet/DFL）。
- 打通 WebRTC 信令与后端输出轨，完成媒体流收发。
- 实现视频输入捕获（`webrtc_client`、`local_cam`、`rtsp`）。
- 完成双GPU流水线并行与队列调度优化。

## 2025-10-30
- [15:33:53] 创建每日标签脚本并更新文档；后端/前端运行稳定。
- [15:41:09] 前端：实现浏览器与本地摄像头采集；实时视频显示与速度/FPS统计。
- [15:44:32] 修复Cockpit采集显示：加入STUN配置与非阻塞统计刷新。
- [15:45:51] 兼容streamlit-webrtc新旧API：确保浏览器视频采集显示。
- [15:48:43] 进一步修复：WebRTC显示与权限提示，确保采集可见。
- [19:43:23] 修复：使用VideoProcessorBase.recv()，移除线程内Streamlit调用，稳定显示。
- [19:50:24] 前端加采集参数：分辨率/帧率约束以缓解卡顿。
- [19:58:39] WebRTC预览放大与设备选择；无本地设备时隐藏选项。
- [20:01:44] 添加日志组件；配置设定为debug模式；日志显示帧与处理耗时。
- [20:05:17] 修复TypeError：移除不兼容参数；加入facingMode约束替代设备选择。
 - [20:12:05] 前端：将本地直显改造为固定 400x400 的 2x3 栅格。
 - [20:12:59] 抽离组件至 `cockpit/grid_ui.py` 并在 `cockpit/app.py` 集成。
 - [20:14:31] 修复 f-string 右花括号转义导致的 SyntaxError；恢复页面可见。
 - [20:16:02] 端口占用切换至 `:8599` 并成功启动；预览地址 `http://localhost:8599`。
 - [20:17:20] 预览验证：2x3 网格渲染正常，浏览器控制台无错误。
 - [20:18:07] 提交并推送：feat(cockpit): extract 2x3 local grid to cockpit/grid_ui.py and integrate; preview at 400x400
- [20:20:11] 补充本次操作记录（OPERATIONS_LOG.md）并同步至远端。
 - [20:28:12] 前端重构：新增 `cockpit/ui_components.py` 封装 UI 组件（Logo/背景、侧边栏、画廊）。
 - [20:29:05] 侧边栏：添加本地摄像头 `local_cam` 与 `rtsp` 条件参数；后端地址移至侧栏。
 - [20:29:57] 语义调整：将“仅原始预览”改为“开启换脸”，内部沿用 `raw_preview` 逻辑。
 - [20:30:31] 画廊：在采集与统计上方新增左右并列选择（左DFM人脸模型，右背景图/视频）。
 - [20:31:22] 顶部：左上角增加 Logo；新增“🖼️”图标按钮用于页面背景图切换。
 - [20:32:06] 移除“启动/停止流水线”按钮（由 START/STOP 控制本地直显）；保留局部逻辑。
- [20:33:10] 预览校验：`http://localhost:8599` UI 加载正常，未见控制台错误。
 - [20:40:55] 前端：新增可持久化配置模块 `cockpit/frontend_config.py`（标题/Logo/背景）。
 - [20:41:37] UI 组件：`render_header_with_logo()` 改为从配置读取并提供背景切换按钮（自动保存）。
 - [20:42:06] 增加 `render_ui_config_editor()` 在侧栏提供标题/Logo/背景的可视化编辑，改动即保存并 `st.rerun()` 应用。
 - [20:42:40] 在 `cockpit/app.py` 集成配置编辑器；页面加载时读取并应用配置。
 - [20:43:10] 预览验证：切换背景开关/替换Logo/编辑标题均可保存与即时刷新。

 - [23:34:02] UI 精简：移除界面内“标题/Logo/背景”可视化编辑器与背景切换按钮，仅从配置读取。
 - [23:36:11] 侧栏新增：OBS 输出控制（开关 + 地址输入）与“打开满屏输出窗口”按钮。
 - [23:38:25] 满屏模式：新增隐藏标题与侧栏的全屏占位页，便于投屏/OBS 采集。
 - [23:41:57] 配置迁移：将 UI 配置从 `assets/user/ui_config.json` 迁移到 `cockpit/ui_config.json`，并新增字段 `obs_enabled`、`obs_url`；实现旧路径到新路径的自动迁移。
 - [23:44:39] 持久化：`cockpit/ui_components.py` 侧栏 OBS 控件读写 `cockpit/ui_config.json`，配置更改即时保存。
 - [23:47:12] 集成：在 `cockpit/app.py` 接入 OBS 控件与满屏逻辑，读取标题/Logo/背景自配置文件。
 - [23:50:33] 修复启动失败：移除 `ui_components.render_obs_controls()` 中的相对导入，解决 Streamlit 非包上下文下的 ImportError。
 - [23:52:01] 重启并验证：前端 `http://localhost:8599/` 启动成功；侧栏 OBS 开关与地址可持久化；满屏页渲染正常。
 - [23:53:40] 变更确认：按用户要求取消“2x3 网格中纯色背景与服务器获取图像交换顺序”任务。
 - [23:55:05] 本次操作归档至本日志，并准备提交推送至 GitHub。
## 2025-10-31

### 归档与版本提交
- 执行仓库归档：添加提交并创建时间戳标签，推送到 GitHub 远程。
- 提交内容：
  - 后端 WebRTC：实现双路视频（前景 + 掩码）接收与服务端合成回传；保持 H.264 编码偏好与连接管理。
  - 前端 Cockpit：在 H.264 传输测试区块中增加掩码轨采集（canvas.captureStream），本地预览与调试输出；与摄像头前景一同发送。
  - 后端配置：支持通过环境变量 `MODEL_URL_*` 覆盖模型下载地址，启动时自动下载到 `assets/models/`。

### 功能更新
- WebRTC `/webrtc/sdp`：新增 `ComposedTrack`，将第一条视频视为前景、第二条视频视为掩码；服务器端根据掩码对前景进行背景合成（默认黑底或 `assets/user/background` 最新图片）。
- Cockpit `media_transport.py`：
  - 增加“发送掩码轨”开关；掩码采用灰度二值化占位实现（后续可替换为更优算法或模型）。
  - 增加掩码本地预览与调试信息输出框。
- 配置 `app/config.py`：通过环境变量设置模型直链地址，实现启动时自动下载。

### 后续计划
- 在前端增加“纯色背景合成窗口”并叠加帧数与 FPS。
- 可选：启用后端 RVM ONNX 完成抠像，移除前端掩码路径或并行保留对比。
