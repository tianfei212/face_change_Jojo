# Fusion Engine & Cockpit

一个基于FastAPI (后端) 与 Streamlit (前端) 的视频AI处理系统骨架，匹配以下架构：

- 前后端分离：后端暴露REST与WebRTC端点，前端作为客户端。
- AI流水线：视频输入 → 面部检测 → 人体抠图 → 精细面部解析 → 换脸推理 → 面部融合 → 最终合成 → WebRTC输出。
- GPU并行：支持单卡与双GPU流水线并行（占位实现）。

## 目录结构

- `app/` 后端FastAPI源码
- `cockpit/` 前端Streamlit Cockpit
- `run.py` 启动后端服务
- `requirements.txt` 依赖清单

## 安装依赖

建议使用Python 3.10+，并在虚拟环境中安装：

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

> 注意：`onnxruntime-gpu` 需要匹配本机CUDA版本。若安装失败，可暂时使用 `onnxruntime` 进行功能演示。

## 运行后端

```bash
python run.py
```

后端默认监听 `http://localhost:8000`。

### API 概览

- `GET /system/status`：系统状态（IDLE/PROCESSING/ERROR, models_ready）。
- `POST /files/upload/face`：上传源人脸图片。
- `POST /files/upload/background`：上传背景图片/视频。
- `POST /stream/start`：启动流水线，需要请求体包含 `use_multi_gpu` 与 `input_source`。
- `POST /stream/stop`：停止流水线。
- `GET /stream/status`：流水线状态。
- `POST /webrtc/sdp`：WebRTC信令占位。

## 运行前端 Cockpit

```bash
streamlit run cockpit/app.py
```

在浏览器中打开 Streamlit 页面，配置后端地址（默认 `http://localhost:8000`），上传资产并启动/停止流水线。

## 模型自动下载

后端在启动时会检查 `/opt/fusion_assets/models/` 目录，并尝试下载：`rvm.onnx`, `retinaface_mnet.onnx`, `bisenet.onnx`, `dfl.onnx`。下载URL在 `app/config.py` 中配置为占位，请替换为真实地址。

## 后续工作

- 在 `ProcessingManager` 中实现各AI模块与GPU并行逻辑。
- 集成 `aiortc` WebRTC接收与发送（`webrtc.py` 与自定义Track）。
- 完善面部检测跟踪与RVM状态传递等优化。