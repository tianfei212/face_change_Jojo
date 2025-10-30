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
