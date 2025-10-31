import asyncio
import time
from typing import Set, Optional

import av
import cv2
from fastapi import APIRouter, Request
from aiortc import (
    RTCPeerConnection,
    RTCSessionDescription,
    VideoStreamTrack,
    RTCRtpSender,
)
from aiortc.contrib.media import MediaRelay


router = APIRouter()

# Keep references to active peer connections to avoid premature GC
pcs: Set[RTCPeerConnection] = set()
relay = MediaRelay()


class ProcessorTrack(VideoStreamTrack):
    """Single-source track that overlays frame counter and FPS."""

    def __init__(self, source: VideoStreamTrack):
        super().__init__()
        self.source = source
        self._counter = 0
        self._last_ts: Optional[float] = None
        self._fps = 0.0

    async def recv(self) -> av.VideoFrame:
        frame = await self.source.recv()
        img = frame.to_ndarray(format="bgr24")
        self._counter += 1
        now = time.time()
        if self._last_ts is not None:
            dt = now - self._last_ts
            if dt > 0:
                inst = 1.0 / dt
                self._fps = (0.9 * self._fps + 0.1 * inst) if self._fps > 0 else inst
        self._last_ts = now

        text = f"Frames: {self._counter}  FPS: {self._fps:.1f}"
        cv2.putText(img, text, (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 0), 2)

        new_frame = av.VideoFrame.from_ndarray(img, format="bgr24")
        new_frame.pts = frame.pts
        new_frame.time_base = frame.time_base
        return new_frame


class ComposedTrack(VideoStreamTrack):
    """
    Compose foreground with an optional low-res mask from a second track.
    - Foreground: main incoming video (camera)
    - Mask: grayscale (0..255) from canvas capture, read asynchronously
    """

    def __init__(self, fg: VideoStreamTrack, mask: Optional[VideoStreamTrack] = None):
        super().__init__()
        self.fg = fg
        self.mask_src = mask
        self._latest_mask: Optional[av.VideoFrame] = None
        self._mask_task: Optional[asyncio.Task] = None
        self._counter = 0
        self._last_ts: Optional[float] = None
        self._fps = 0.0
        if self.mask_src is not None:
            self._mask_task = asyncio.create_task(self._pump_mask())

    async def _pump_mask(self):
        try:
            while True:
                frame = await self.mask_src.recv()
                self._latest_mask = frame
        except Exception:
            # Mask stream ended or error; stop updating
            self._latest_mask = None

    def attach_mask(self, mask: VideoStreamTrack):
        self.mask_src = mask
        if self._mask_task is None:
            self._mask_task = asyncio.create_task(self._pump_mask())

    async def recv(self) -> av.VideoFrame:
        fg_frame = await self.fg.recv()
        img = fg_frame.to_ndarray(format="bgr24")

        # Stats
        self._counter += 1
        now = time.time()
        if self._last_ts is not None:
            dt = now - self._last_ts
            if dt > 0:
                inst = 1.0 / dt
                self._fps = (0.9 * self._fps + 0.1 * inst) if self._fps > 0 else inst
        self._last_ts = now

        # If mask available, compose foreground with simple alpha cutout on black bg
        mask_frame = self._latest_mask
        if mask_frame is not None:
            try:
                m = mask_frame.to_ndarray(format="gray")
                # Resize mask to match foreground size
                if m.shape[0] != img.shape[0] or m.shape[1] != img.shape[1]:
                    m = cv2.resize(m, (img.shape[1], img.shape[0]), interpolation=cv2.INTER_LINEAR)
                alpha = (m.astype("float32") / 255.0).reshape(img.shape[0], img.shape[1], 1)
                # Black background composition
                img = (img.astype("float32") * alpha).astype("uint8")
            except Exception:
                pass

        # Overlay HUD
        text = f"Frames: {self._counter}  FPS: {self._fps:.1f}"
        cv2.putText(img, text, (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 0), 2)

        out = av.VideoFrame.from_ndarray(img, format="bgr24")
        out.pts = fg_frame.pts
        out.time_base = fg_frame.time_base
        return out


@router.post("/sdp")
async def sdp_exchange(request: Request):
    """
    WebRTC SDP exchange endpoint.
    - Receives offer from front-end (H.264 preferred).
    - Decodes incoming video, overlays frame count and FPS.
    - Re-encodes and sends processed video back (prefer H.264).
    """

    data = await request.json()
    offer = RTCSessionDescription(sdp=data["sdp"], type=data["type"])

    pc = RTCPeerConnection()
    pcs.add(pc)

    @pc.on("connectionstatechange")
    async def on_connectionstatechange():
        if pc.connectionState in ("closed", "failed", "disconnected"):
            try:
                pcs.discard(pc)
                await pc.close()
            except Exception:
                pass

    # Per-connection composition state
    composed_track: Optional[ComposedTrack] = None

    @pc.on("track")
    def on_track(track):
        if track.kind != "video":
            return
        subscribed = relay.subscribe(track)
        nonlocal composed_track
        if composed_track is None:
            # First video as foreground
            composed_track = ComposedTrack(subscribed)
            pc.addTrack(composed_track)
        else:
            # Second video as mask
            composed_track.attach_mask(subscribed)

        # Prefer H.264 for outbound video when available
        try:
            codecs = RTCRtpSender.getCapabilities("video").codecs
            h264_codecs = [c for c in codecs if c.name == "H264"]
            for t in pc.getTransceivers():
                if t.kind == "video" and h264_codecs:
                    t.setCodecPreferences(h264_codecs)
        except Exception:
            pass

    await pc.setRemoteDescription(offer)
    # Create and set local answer
    answer = await pc.createAnswer()
    await pc.setLocalDescription(answer)

    # Return answer for the browser to complete handshake
    return {"sdp": pc.localDescription.sdp, "type": pc.localDescription.type}