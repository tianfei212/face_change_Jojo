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
        }} catch (e) {{
          hud.textContent = '无法打开摄像头: ' + e.message;
        }}
      }}
      if (enabled) startStream(); else stopStream();
    }})();
    </script>
    """

    components.html(html, height=860)
