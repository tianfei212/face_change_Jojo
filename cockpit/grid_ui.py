def render_local_2x3_grid(enabled: bool, W: int, H: int, fps_target: int, facing_mode: str, bg_color: str) -> None:
    import streamlit.components.v1 as components

    fm = f'"{facing_mode}"' if facing_mode != "auto" else 'undefined'
    html = f"""
    <div id=\"grid-wrap\" style=\"width:100%;overflow:auto;margin:0 auto\">
      <style>
        .grid6 {{ display:grid; grid-template-columns: repeat(3, 400px); grid-auto-rows: 400px; gap: 12px; justify-content:center; }}
        .cell {{ position:relative; width:400px; height:400px; background:#000; border:1px solid #444; border-radius:6px; overflow:hidden; }}
        .cell video, .cell img, .cell canvas {{ width:100%; height:100%; object-fit: cover; display:block; background:#000; }}
        .label {{ position:absolute; left:8px; top:8px; color:#fff; background:rgba(0,0,0,.45); padding:4px 6px; border-radius:4px; font:13px/1.3 sans-serif; }}
      </style>
      <div class=\"grid6\">
        <div class=\"cell\">
          <video id=\"localPreview\" autoplay muted playsinline></video>
          <div class=\"label\">原始视频</div>
          <div id=\"hud\" style=\"position:absolute;right:8px;top:8px;color:#0f0;background:rgba(0,0,0,.4);padding:2px 4px;border-radius:4px;font:12px/1.3 monospace\">帧: 0 | FPS: 0.0</div>
        </div>
       
        <div class=\"cell\">
          <div id=\"solidColor\" style=\"width:100%;height:100%;background:{bg_color};\"></div>
          <div class=\"label\">纯色背景</div>
        </div>
         <div class=\"cell\">
          <img id=\"serverImage\" alt=\"服务器获取图像\" />
          <div class=\"label\">服务器获取图像</div>
        </div>
        <div class=\"cell\">
          <canvas id=\"faceDetect\"></canvas>
          <div class=\"label\">人脸检测</div>
        </div>
        <div class=\"cell\">
          <canvas id=\"faceSwap\"></canvas>
          <div class=\"label\">人脸替换</div>
        </div>
        <div class=\"cell\">
          <canvas id=\"bgMerge\"></canvas>
          <div class=\"label\">背景合并</div>
        </div>
      </div>
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

      function paintPlaceholder(id, text) {{
        const c = document.getElementById(id);
        if (!c) return;
        const dpr = window.devicePixelRatio || 1;
        c.width = 400 * dpr; c.height = 400 * dpr; c.style.width = '400px'; c.style.height = '400px';
        const g = c.getContext('2d');
        g.scale(dpr, dpr);
        g.fillStyle = '#111'; g.fillRect(0,0,400,400);
        g.strokeStyle = '#333';
        for (let i=0;i<400;i+=20) {{ g.beginPath(); g.moveTo(i,0); g.lineTo(0,i); g.stroke(); }}
        g.fillStyle = '#bbb'; g.font = '16px sans-serif'; g.textAlign = 'center';
        g.fillText(text, 200, 200);
      }}

      // 初始化占位画面
      paintPlaceholder('faceDetect', '人脸检测 占位');
      paintPlaceholder('faceSwap', '人脸替换 占位');
      paintPlaceholder('bgMerge', '背景合并 占位');

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
            setInterval(() => {{ hud.textContent = `FPS 估计中...`; }}, 1000);
          }}

          // 在“纯色背景”单元挂载合成画面（前景 + 掩码）
          try {{
            const solidWrap = document.getElementById('solidColor');
            if (solidWrap) {{
              const dpr = window.devicePixelRatio || 1;
              const CW = 400, CH = 400; // 与 cell 尺寸一致
              const W = Math.floor(CW * dpr), H = Math.floor(CH * dpr);
              // 创建显示画布
              solidWrap.innerHTML = '';
              const solidCanvas = document.createElement('canvas');
              solidCanvas.width = W; solidCanvas.height = H;
              solidCanvas.style.width = CW + 'px';
              solidCanvas.style.height = CH + 'px';
              solidCanvas.style.display = 'block';
              solidCanvas.style.background = '{bg_color}';
              solidWrap.appendChild(solidCanvas);
              const sctx = solidCanvas.getContext('2d');
              sctx.scale(dpr, dpr);

              // 离屏缓冲用于读取像素
              const off = document.createElement('canvas');
              off.width = CW; off.height = CH;
              const octx = off.getContext('2d', {{ willReadFrequently: true }});

              let fCount = 0, lastF = performance.now(), fpsSolid = 0;
              function drawOnce() {{
                // 背景填充为纯色
                sctx.save();
                sctx.scale(1, 1); // dpr 已在 ctx 上设置
                sctx.fillStyle = '{bg_color}';
                sctx.fillRect(0, 0, CW, CH);

                // 将前景按比例绘制到离屏
                const vw = v.videoWidth || CW, vh = v.videoHeight || CH;
                const scale = Math.min(CW / vw, CH / vh);
                const dw = Math.max(1, Math.floor(vw * scale));
                const dh = Math.max(1, Math.floor(vh * scale));
                const dx = Math.floor((CW - dw) / 2);
                const dy = Math.floor((CH - dh) / 2);
                octx.clearRect(0,0,CW,CH);
                if (dw > 0 && dh > 0) {{
                  octx.drawImage(v, dx, dy, dw, dh);
                }}

                // 读取前景像素并在本组件内生成掩码（占位算法：亮度自适应阈值）
                const fgImg = octx.getImageData(0,0,CW,CH);
                const fg = fgImg.data;
                // 计算平均亮度，作为动态阈值基础
                let sumY = 0;
                for (let i = 0; i < fg.length; i += 4) {{
                  const r = fg[i], g = fg[i+1], b = fg[i+2];
                  sumY += 0.2126*r + 0.7152*g + 0.0722*b;
                }}
                const meanY = sumY / (CW * CH);
                const thr = Math.min(255, Math.max(0, meanY * 0.9)); // 自适应阈值

                // 合成：根据自适应亮度阈值构造二值掩码并叠加到纯色底
                for (let i = 0; i < fg.length; i += 4) {{
                  const r = fg[i], g = fg[i+1], b = fg[i+2];
                  const y = 0.2126*r + 0.7152*g + 0.0722*b;
                  const a = y > thr ? 255 : 0; // 简单二值掩码
                  fg[i]   = (r * a) / 255;
                  fg[i+1] = (g * a) / 255;
                  fg[i+2] = (b * a) / 255;
                  fg[i+3] = 255;
                }}

                sctx.putImageData(fgImg, 0, 0);

                // HUD: 统计并叠加帧数/FPS
                fCount++;
                const now = performance.now();
                const dt = now - lastF;
                if (dt >= 1000) {{ fpsSolid = (fCount * 1000) / dt; fCount = 0; lastF = now; }}
                sctx.fillStyle = 'rgba(0,0,0,0.5)';
                sctx.fillRect(8, 8, 180, 28);
                sctx.fillStyle = '#0f0';
                sctx.font = 'bold 13px monospace';
                sctx.fillText('帧: ' + fCount + ' FPS: ' + fpsSolid.toFixed(1), 12, 28);
                sctx.restore();
              }}

              // 优先用 requestVideoFrameCallback 驱动绘制，退化到 rAF
              const step = () => {{ drawOnce(); requestAnimationFrame(step); }};
              requestAnimationFrame(step);
            }}
          }} catch (e) {{
            console.warn('纯色背景合成失败: ', e);
          }}
        }} catch (e) {{
          hud.textContent = '无法打开摄像头: ' + e.message;
        }}
      }}
      if (enabled) startStream(); else stopStream();
    }})();
    </script>
    """

    components.html(html, height=860)
