import asyncio
import time
from typing import Set

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
    """Video track that overlays frame counter and FPS on incoming frames."""

    def __init__(self, source: VideoStreamTrack):
        super().__init__()
        self.source = source
        self._counter = 0
        self._last_ts = None
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
                # EMA smoothing for FPS
                self._fps = (0.9 * self._fps + 0.1 * inst) if self._fps > 0 else inst
        self._last_ts = now

        text = f"Frames: {self._counter}  FPS: {self._fps:.1f}"
        cv2.putText(img, text, (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 0), 2)

        new_frame = av.VideoFrame.from_ndarray(img, format="bgr24")
        # Preserve timing when possible
        new_frame.pts = frame.pts
        new_frame.time_base = frame.time_base
        return new_frame


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

    @pc.on("track")
    def on_track(track):
        if track.kind == "video":
            # Relay and process frames
            subscribed = relay.subscribe(track)
            processed = ProcessorTrack(subscribed)
            pc.addTrack(processed)

            # Prefer H.264 for outbound video when available
            try:
                codecs = RTCRtpSender.getCapabilities("video").codecs
                h264_codecs = [c for c in codecs if c.name == "H264"]
                for t in pc.getTransceivers():
                    if t.kind == "video" and h264_codecs:
                        t.setCodecPreferences(h264_codecs)
            except Exception:
                # Fallback silently if preferences cannot be set
                pass

    await pc.setRemoteDescription(offer)
    # Create and set local answer
    answer = await pc.createAnswer()
    await pc.setLocalDescription(answer)

    # Return answer for the browser to complete handshake
    return {"sdp": pc.localDescription.sdp, "type": pc.localDescription.type}