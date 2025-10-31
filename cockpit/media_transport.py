import os
import json
import streamlit as st


def render_h264_transport_ui(backend: str, facing_mode: str = "user") -> None:
    """
    渲染一个基于 WebRTC 的 H.264 视频传输测试区块：
    - 采集本地摄像头，首选 H.264 编码推送到后端信令。
    - 接收后端处理后的视频并在指定窗口中显示。
    - 使用 /webrtc/sdp 进行简单的信令交换（占位）。

    说明：浏览器负责编码与解码，若支持 H.264，将优先选择该编码；否则回退到默认。
    额外：为了支持“方案2（前景 + 掩码双路）”，此模块会从 Canvas 捕获一条低分辨率的掩码视频轨并与前景一同发送到后端。
    """
    _backend_js = json.dumps(backend)
    _facing_js = json.dumps(facing_mode)
    # 避免 f-string 与 JS 花括号冲突，使用占位符并后续替换注入
    html = """
    <div id=\"rtcWrap\" style=\"border:1px solid #ddd;border-radius:8px;padding:10px;margin:8px 0;background:#111\">
      <div style=\"display:flex;gap:12px;align-items:center;\">
        <button id=\"btnStart\" style=\"padding:8px 12px;border-radius:6px;border:1px solid #3a3a3a;background:#1e1e1e;color:#fff\">开始 H.264 传输</button>
        <button id=\"btnStop\" style=\"padding:8px 12px;border-radius:6px;border:1px solid #3a3a3a;background:#1e1e1e;color:#fff\">停止</button>
        <div id=\"rtcStatus\" style=\"color:#9acd32;font:13px/1.3 monospace\">Idle</div>
        <label style=\"margin-left:auto;color:#ccc;font:12px/1.2 sans-serif\"><input id=\"maskToggle\" type=\"checkbox\" checked /> 发送掩码轨（低分辨率）</label>
      </div>
      <div style=\"display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-top:10px\">
        <div>
          <div style=\"color:#aaa;margin-bottom:6px\">本地预览</div>
          <video id=\"localCam\" autoplay muted playsinline style=\"width:100%;height:auto;background:#000;border-radius:6px\"></video>
        </div>
        <div>
          <div style=\"color:#aaa;margin-bottom:6px\">后端处理（远端）</div>
          <video id=\"remoteProcessed\" autoplay playsinline controls style=\"width:100%;height:auto;background:#000;border-radius:6px\"></video>
        </div>
      </div>
      <div style=\"display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-top:10px\">
        <div>
          <div style=\"color:#aaa;margin-bottom:6px\">掩码预览（本地生成）</div>
          <canvas id=\"maskCanvas\" width=\"320\" height=\"180\" style=\"width:100%;height:auto;background:#111;border-radius:6px\"></canvas>
        </div>
        <div>
          <div style=\"color:#aaa;margin-bottom:6px\">调试信息</div>
          <pre id=\"dbg\" style=\"margin:0;color:#8f8;background:#222;padding:8px;border-radius:6px;max-height:180px;overflow:auto;font:12px/1.4 monospace\"></pre>
        </div>
      </div>
    </div>
    <script>
    (function(){
      const backend = __BACKEND__;
      const facing = __FACING__;
      const btnStart = document.getElementById('btnStart');
      const btnStop = document.getElementById('btnStop');
      const localV = document.getElementById('localCam');
      const remoteV = document.getElementById('remoteProcessed');
      const statusEl = document.getElementById('rtcStatus');
      const maskToggle = document.getElementById('maskToggle');
      const maskCanvas = document.getElementById('maskCanvas');
      const dbg = document.getElementById('dbg');
      let pc = null, localStream = null;
      let maskStream = null, maskTrack = null;
      let maskRunning = false;

      function setStatus(t){ statusEl.textContent = t; }
      function logDbg(t){ try{ dbg.textContent = t + "\n" + dbg.textContent.substring(0, 2000);}catch(_){} }

      async function start(){
        try {
          setStatus('Starting...');
          const rtcConfig = { iceServers: [{ urls: 'stun:stun.l.google.com:19302' }] };
          pc = new RTCPeerConnection(rtcConfig);
          pc.oniceconnectionstatechange = () => setStatus('ICE: ' + pc.iceConnectionState);
          pc.onconnectionstatechange = () => setStatus('PC: ' + pc.connectionState);
          pc.ontrack = (ev) => { remoteV.srcObject = ev.streams[0]; };

          // 摄像头采集
          const constraints = { video: { facingMode: facing }, audio: false };
          localStream = await navigator.mediaDevices.getUserMedia(constraints);
          localV.srcObject = localStream;
          // 先添加前景轨
          localStream.getTracks().forEach(t => pc.addTrack(t, localStream));

          // 若勾选，构造掩码轨（低分辨率）并作为第二条视频发送
          if (maskToggle.checked) {
            const W = maskCanvas.width, H = maskCanvas.height;
            const ctx = maskCanvas.getContext('2d', { willReadFrequently: true });
            if (!ctx) throw new Error('Canvas 2D context unavailable');
            maskRunning = true;
            const fps = 15;
            // 以固定帧率捕获掩码画面
            function step(){
              if (!maskRunning) return;
              try {
                // 将摄像头帧绘制到 canvas 并生成简易掩码（亮度阈值）
                const v = localV;
                const vw = v.videoWidth || 640, vh = v.videoHeight || 360;
                // 保持纵横比居中缩放
                const s = Math.min(W / vw, H / vh);
                const dw = Math.max(1, Math.floor(vw * s)), dh = Math.max(1, Math.floor(vh * s));
                const dx = Math.floor((W - dw) / 2), dy = Math.floor((H - dh) / 2);
                ctx.clearRect(0, 0, W, H);
                ctx.drawImage(v, dx, dy, dw, dh);
                const img = ctx.getImageData(0, 0, W, H);
                const p = img.data;
                // 生成灰度掩码：简单亮度阈值（占位，后续可替换为更优算法/模型）
                let sum=0;
                for (let i = 0; i < p.length; i += 4) {
                  const r = p[i], g = p[i+1], b = p[i+2];
                  const y = (0.2126*r + 0.7152*g + 0.0722*b);
                  const m = y > 64 ? 255 : 0; // 简单二值化阈值
                  p[i] = m; p[i+1] = m; p[i+2] = m; // 灰度
                  // alpha 保持不变
                  sum += m;
                }
                ctx.putImageData(img, 0, 0);
                logDbg(`mask avg=${(sum/(W*H)).toFixed(1)} time=${Date.now()%100000}`);
              } catch(e) {}
              setTimeout(step, Math.floor(1000/fps));
            }
            step();
            maskStream = maskCanvas.captureStream(fps);
            maskTrack = maskStream.getVideoTracks()[0];
            pc.addTrack(maskTrack, maskStream);
          }

          // 优先选择 H.264 编码（若浏览器支持）
          try {
            const transceivers = pc.getTransceivers();
            transceivers.forEach(tr => {
              const caps = RTCRtpSender.getCapabilities && RTCRtpSender.getCapabilities('video');
              if (caps && tr && tr.setCodecPreferences) {
                const h264 = (caps.codecs || []).filter(c => (c.mimeType || '').toLowerCase() === 'video/h264');
                if (h264.length) tr.setCodecPreferences(h264);
              }
            });
          } catch (e) {}

          const offer = await pc.createOffer({ offerToReceiveVideo: true, offerToReceiveAudio: false });
          await pc.setLocalDescription(offer);

          // 简单信令交换（后端占位接口）
          const resp = await fetch(backend + '/webrtc/sdp', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ sdp: offer.sdp, type: 'offer' })
          });
          const data = await resp.json();
          if (data && data.sdp) {
            const answer = { type: 'answer', sdp: data.sdp };
            await pc.setRemoteDescription(answer);
            setStatus('Connected (answer received)');
          } else {
            setStatus('Awaiting backend integration (placeholder answer)');
          }
        } catch (e) {
          console.error(e); setStatus('Error: ' + e.message);
        }
      }

      function stop(){
        try {
          if (pc) { pc.getSenders().forEach(s => { try { s.track && s.track.stop(); } catch(_){} }); pc.close(); }
          if (localStream) { localStream.getTracks().forEach(t => { try{ t.stop(); }catch(_){ } }); }
          if (maskTrack) { try{ maskTrack.stop(); }catch(_){ } }
          maskRunning = false; maskStream = null; maskTrack = null;
        } finally {
          pc = null; localStream = null; setStatus('Stopped');
        }
      }

      btnStart.addEventListener('click', start);
      btnStop.addEventListener('click', stop);
      window.addEventListener('beforeunload', stop);
    })();
    </script>
    """
    html = html.replace("__BACKEND__", _backend_js).replace("__FACING__", _facing_js)
    import streamlit.components.v1 as components
    components.html(html, height=520)