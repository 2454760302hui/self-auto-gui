import type { MouseEvent, WheelEvent } from 'react';
import { useCallback, useEffect, useRef, useState } from 'react';
import type { Socket } from 'socket.io-client';
import { io } from 'socket.io-client';
import { ScrcpyVideoCodecId } from '@yume-chan/scrcpy';
import {
  BitmapVideoFrameRenderer,
  WebCodecsVideoDecoder,
  WebGLVideoFrameRenderer,
} from '@yume-chan/scrcpy-decoder-webcodecs';
import {
  getScreenshot,
  sendKeyEvent,
  sendTextInput,
  sendSwipe,
  sendTouchDown,
  sendTouchMove,
  sendTouchUp,
} from '../api';
import { detectWebCodecsUnavailabilityReason } from '../lib/webcodecs-utils';
import { AlertCircle } from 'lucide-react';

const MOTION_THROTTLE_MS = 50;
const WHEEL_DELAY_MS = 300;

interface ScrcpyPlayerProps {
  deviceId: string;
  className?: string;
  onFallback?: (reason?: string) => void;
  fallbackTimeout?: number;
  enableControl?: boolean;
  onTapSuccess?: (x: number, y: number) => void;
  onTapError?: (error: string) => void;
  onSwipeSuccess?: (sx: number, sy: number, ex: number, ey: number) => void;
  onSwipeError?: (error: string) => void;
  onStreamReady?: (stream: { close: () => void } | null) => void;
  isVisible?: boolean;
  /** Screenshot shown as background when the stream is not yet connected or failed. */
  fallbackScreenshot?: string | null;
  /** Called with actual device screen dimensions once stream metadata arrives. */
  onScreenInfo?: (info: { width: number; height: number }) => void;
  /** Called after every successful control action (tap, swipe, key, text). */
  onControlAction?: () => void;
}

interface VideoMetadata {
  deviceName?: string;
  width?: number;
  height?: number;
  codec?: number;
}

interface VideoPacket {
  type: 'configuration' | 'data';
  data: ArrayBuffer | Uint8Array;
  keyframe?: boolean;
  pts?: number;
}

export function ScrcpyPlayer({
  deviceId,
  className,
  onFallback,
  fallbackTimeout = 8000,
  enableControl = false,
  onTapSuccess,
  onTapError,
  onSwipeSuccess,
  onSwipeError,
  onStreamReady,
  isVisible = true, // ✅ 默认 true，向后兼容
  fallbackScreenshot,
  onScreenInfo,
  onControlAction,
}: ScrcpyPlayerProps) {
  const socketRef = useRef<Socket | null>(null);
  const decoderRef = useRef<WebCodecsVideoDecoder | null>(null);
  const videoContainerRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const fallbackTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const connectDeviceRef = useRef<(() => void) | null>(null);
  const hasReceivedDataRef = useRef(false);
  const suppressReconnectRef = useRef(false);
  const onFallbackRef = useRef(onFallback);
  const fallbackTimeoutRef = useRef(fallbackTimeout);
  const onStreamReadyRef = useRef(onStreamReady);
  const isVisibleRef = useRef(isVisible); // ✅ 新增：用 ref 追踪 isVisible
  const onControlActionRef = useRef(onControlAction);
  const hasFallbackRef = useRef(!!fallbackScreenshot);

  const [status, setStatus] = useState<
    'connecting' | 'connected' | 'error' | 'disconnected'
  >('connecting');
  // 控制事件在 'connected' 状态或有 fallback screenshot 时才允许
  const [controlEnabled, setControlEnabled] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [screenInfo, setScreenInfo] = useState<{
    width: number;
    height: number;
  } | null>(null);
  const [deviceResolution, setDeviceResolution] = useState<{
    width: number;
    height: number;
  } | null>(null);

  const isDraggingRef = useRef(false);
  const dragStartRef = useRef<{ x: number; y: number } | null>(null);
  const movedRef = useRef(false);
  const swipeStartRef = useRef<{ x: number; y: number } | null>(null);
  const lastMoveTimeRef = useRef<number>(0);
  const pendingMoveRef = useRef<{ x: number; y: number } | null>(null);
  const moveThrottleTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const wheelTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const accumulatedScrollRef = useRef<{ deltaY: number } | null>(null);

  useEffect(() => {
    onFallbackRef.current = onFallback;
    fallbackTimeoutRef.current = fallbackTimeout;
    onStreamReadyRef.current = onStreamReady;
    isVisibleRef.current = isVisible; // ✅ 新增：用 ref 追踪 isVisible
    onControlActionRef.current = onControlAction;
    hasFallbackRef.current = !!fallbackScreenshot;
    setControlEnabled(status === 'connected' || !!fallbackScreenshot);
  }, [onFallback, fallbackTimeout, onStreamReady, isVisible, onControlAction, fallbackScreenshot, status]);

  useEffect(() => {
    const fetchDeviceResolution = async () => {
      try {
        const screenshot = await getScreenshot(deviceId);
        if (screenshot.success) {
          setDeviceResolution({
            width: screenshot.width,
            height: screenshot.height,
          });
        }
      } catch (error) {
        console.error(
          '[ScrcpyPlayer] Failed to fetch device resolution:',
          error
        );
      }
    };

    fetchDeviceResolution();
  }, [deviceId]);

  const updateCanvasSize = useCallback(() => {
    const canvas = canvasRef.current;
    const container = videoContainerRef.current;
    if (!canvas || !container || !screenInfo) return;

    const containerWidth = container.clientWidth;
    const containerHeight = container.clientHeight;
    const { width: originalWidth, height: originalHeight } = screenInfo;

    const aspectRatio = originalWidth / originalHeight;
    let targetWidth = containerWidth;
    let targetHeight = containerWidth / aspectRatio;

    if (targetHeight > containerHeight) {
      targetHeight = containerHeight;
      targetWidth = containerHeight * aspectRatio;
    }

    canvas.width = originalWidth;
    canvas.height = originalHeight;
    canvas.style.width = `${targetWidth}px`;
    canvas.style.height = `${targetHeight}px`;
  }, [screenInfo]);

  useEffect(() => {
    const handleResize = () => updateCanvasSize();
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, [updateCanvasSize]);

  useEffect(() => {
    updateCanvasSize();
  }, [screenInfo, updateCanvasSize]);

  const createVideoFrameRenderer = useCallback(async () => {
    if (WebGLVideoFrameRenderer.isSupported) {
      const renderer = new WebGLVideoFrameRenderer();
      return {
        renderer,
        element: renderer.canvas as HTMLCanvasElement,
      };
    }

    const renderer = new BitmapVideoFrameRenderer();
    return {
      renderer,
      element: renderer.canvas as HTMLCanvasElement,
    };
  }, []);

  const createDecoder = useCallback(
    async (codecId: ScrcpyVideoCodecId) => {
      if (!WebCodecsVideoDecoder.isSupported) {
        const reason =
          detectWebCodecsUnavailabilityReason() || 'decoder_unsupported';
        onFallbackRef.current?.(reason);
        throw new Error(
          'Current browser does not support WebCodecs API. Please use the latest Chrome/Edge.'
        );
      }

      const { renderer, element } = await createVideoFrameRenderer();
      canvasRef.current = element;

      // Only append if not already appended (check if canvas is in DOM)
      if (videoContainerRef.current && !element.parentElement) {
        videoContainerRef.current.appendChild(element);
      }

      return new WebCodecsVideoDecoder({
        codec: codecId,
        renderer,
      });
    },
    [createVideoFrameRenderer]
  );

  const markDataReceived = useCallback(() => {
    if (hasReceivedDataRef.current) return;
    hasReceivedDataRef.current = true;
    if (fallbackTimerRef.current) {
      clearTimeout(fallbackTimerRef.current);
      fallbackTimerRef.current = null;
    }
  }, []);

  const setupVideoStream = useCallback(
    (_metadata: VideoMetadata) => {
      let configurationPacketSent = false;
      let pendingDataPackets: VideoPacket[] = [];

      const transformStream = new TransformStream<VideoPacket, VideoPacket>({
        transform(packet, controller) {
          if (packet.type === 'configuration') {
            controller.enqueue(packet);
            configurationPacketSent = true;

            if (pendingDataPackets.length > 0) {
              pendingDataPackets.forEach(p => controller.enqueue(p));
              pendingDataPackets = [];
            }
            return;
          }

          if (packet.type === 'data' && !configurationPacketSent) {
            pendingDataPackets.push(packet);
            return;
          }

          controller.enqueue(packet);
        },
      });

      const videoStream = new ReadableStream<VideoPacket>({
        start(controller) {
          let streamClosed = false;

          const videoDataHandler = (data: VideoPacket) => {
            if (streamClosed) return;
            try {
              markDataReceived();
              const payload = {
                ...data,
                data:
                  data.data instanceof Uint8Array
                    ? data.data
                    : new Uint8Array(data.data),
              };
              controller.enqueue(payload);
            } catch (error) {
              console.error('[ScrcpyPlayer] Video enqueue error:', error);
              streamClosed = true;
              cleanup();
            }
          };

          const errorHandler = (error: { message?: string }) => {
            if (streamClosed) return;
            controller.error(new Error(error?.message || 'Socket error'));
            streamClosed = true;
            cleanup();
          };

          const disconnectHandler = () => {
            if (streamClosed) return;
            controller.close();
            streamClosed = true;
            cleanup();
          };

          const cleanup = () => {
            socketRef.current?.off('video-data', videoDataHandler);
            socketRef.current?.off('error', errorHandler);
            socketRef.current?.off('disconnect', disconnectHandler);
          };

          socketRef.current?.on('video-data', videoDataHandler);
          socketRef.current?.on('error', errorHandler);
          socketRef.current?.on('disconnect', disconnectHandler);

          return () => {
            streamClosed = true;
            cleanup();
          };
        },
      });

      return videoStream.pipeThrough(transformStream);
    },
    [markDataReceived]
  );

  const disconnectDevice = useCallback(
    (suppressReconnect = false) => {
      console.log(`[ScrcpyPlayer] [${deviceId}] Disconnecting...`, {
        suppressReconnect,
        isVisible: isVisibleRef.current,
        socketConnected: socketRef.current?.connected,
      }); // ✅ 方案 3：断开日志

      if (suppressReconnect) {
        suppressReconnectRef.current = true;
      }
      if (decoderRef.current) {
        try {
          decoderRef.current.dispose();
        } catch (error) {
          console.error('[ScrcpyPlayer] Failed to dispose decoder:', error);
        }
        decoderRef.current = null;
      }

      // Just clear the reference, let React handle DOM cleanup
      canvasRef.current = null;

      if (socketRef.current) {
        socketRef.current.disconnect();
        socketRef.current = null;
      }

      onStreamReadyRef.current?.(null);

      if (reconnectTimerRef.current) {
        clearTimeout(reconnectTimerRef.current);
        reconnectTimerRef.current = null;
      }

      if (fallbackTimerRef.current) {
        clearTimeout(fallbackTimerRef.current);
        fallbackTimerRef.current = null;
      }

      setStatus('disconnected');
      setScreenInfo(null);
      setErrorMessage(null);
    },
    [deviceId]
  );

  const connectDevice = useCallback(() => {
    console.log(`[ScrcpyPlayer] [${deviceId}] Connecting...`, {
      isVisible: isVisibleRef.current,
      suppressReconnect: suppressReconnectRef.current,
    }); // ✅ 方案 3：连接日志

    disconnectDevice(true);
    hasReceivedDataRef.current = false;
    setStatus('connecting');
    setErrorMessage(null);

    const socket = io(window.location.origin, {
      path: '/socket.io',
      transports: ['polling', 'websocket'],
      timeout: 10000,
    });
    socketRef.current = socket;

    socket.on('connect', () => {
      console.log(
        `[ScrcpyPlayer] [${deviceId}] Socket connected, emitting connect-device`
      ); // ✅ 方案 3
      socket.emit('connect-device', {
        device_id: deviceId,
        maxSize: 1280,
        bitRate: 4_000_000,
      });

      fallbackTimerRef.current = setTimeout(() => {
        if (!hasReceivedDataRef.current) {
          setStatus('error');
          setErrorMessage('Video stream timeout');
          suppressReconnectRef.current = true;
          socket.close();
          onFallbackRef.current?.();
        }
      }, fallbackTimeoutRef.current);
    });

    socket.on('video-metadata', async (metadata: VideoMetadata) => {
      try {
        if (decoderRef.current) {
          decoderRef.current.dispose();
          decoderRef.current = null;
        }

        const codecId = metadata?.codec
          ? (metadata.codec as ScrcpyVideoCodecId)
          : ScrcpyVideoCodecId.H264;

        decoderRef.current = await createDecoder(codecId);
        decoderRef.current.sizeChanged(({ width, height }) => {
          setScreenInfo({ width, height });
          onScreenInfo?.({ width, height });
        });

        const videoStream = setupVideoStream(metadata);
        videoStream
          .pipeTo(decoderRef.current.writable as WritableStream<VideoPacket>)
          .catch((error: Error) => {
            console.error('[ScrcpyPlayer] Video stream error:', error);
          });

        setStatus('connected');
        console.log('[ScrcpyPlayer] Status set to connected, enableControl:', enableControl, 'deviceId:', deviceId);
        onStreamReadyRef.current?.({ close: () => socket.close() });
      } catch (error) {
        console.error('[ScrcpyPlayer] Decoder initialization failed:', error);
        setStatus('error');
        setErrorMessage('Decoder initialization failed');
        suppressReconnectRef.current = true;
        socket.close();
        const reason = detectWebCodecsUnavailabilityReason() || 'decoder_error';
        onFallbackRef.current?.(reason);
      }
    });

    socket.on('error', (error: { message?: string }) => {
      console.error(`[ScrcpyPlayer] [${deviceId}] Socket error:`, error, {
        suppressReconnect: suppressReconnectRef.current,
        isVisible: isVisibleRef.current,
      }); // ✅ 方案 3：错误日志

      setStatus('error');
      setErrorMessage(error?.message || 'Socket error');

      if (suppressReconnectRef.current) {
        return;
      }

      // ✅ 方案 1：检查 isVisible，隐藏时不重连
      if (!isVisibleRef.current) {
        console.log(
          `[ScrcpyPlayer] [${deviceId}] Skipping reconnect on error (not visible)`
        );
        onStreamReadyRef.current?.(null);
        return;
      }

      onStreamReadyRef.current?.(null);

      if (!reconnectTimerRef.current) {
        console.log(
          `[ScrcpyPlayer] [${deviceId}] Scheduling reconnect after error in 3s`
        ); // ✅ 方案 3
        reconnectTimerRef.current = setTimeout(() => {
          reconnectTimerRef.current = null;
          connectDeviceRef.current?.();
        }, 3000);
      }
    });

    socket.on('disconnect', () => {
      console.log(`[ScrcpyPlayer] [${deviceId}] Socket disconnected`, {
        suppressReconnect: suppressReconnectRef.current,
        isVisible: isVisibleRef.current,
        reconnectTimerActive: !!reconnectTimerRef.current,
      }); // ✅ 方案 3：断连日志

      if (suppressReconnectRef.current) {
        suppressReconnectRef.current = false;
        return;
      }

      // ✅ 方案 1：检查 isVisible，隐藏时不重连
      if (!isVisibleRef.current) {
        console.log(
          `[ScrcpyPlayer] [${deviceId}] Skipping reconnect (not visible)`
        );
        setStatus('disconnected');
        onStreamReadyRef.current?.(null);
        return;
      }

      setStatus('disconnected');
      onStreamReadyRef.current?.(null);

      if (!reconnectTimerRef.current) {
        console.log(`[ScrcpyPlayer] [${deviceId}] Scheduling reconnect in 3s`); // ✅ 方案 3
        reconnectTimerRef.current = setTimeout(() => {
          console.log(`[ScrcpyPlayer] [${deviceId}] Reconnecting now`); // ✅ 方案 3
          reconnectTimerRef.current = null;
          connectDeviceRef.current?.();
        }, 3000);
      }
    });
  }, [deviceId, disconnectDevice, createDecoder, setupVideoStream]);

  useEffect(() => {
    connectDeviceRef.current = connectDevice;
  }, [connectDevice]);

  useEffect(() => {
    // Use queueMicrotask to avoid synchronous setState within effect
    queueMicrotask(() => {
      connectDevice();
    });

    return () => {
      if (moveThrottleTimerRef.current) {
        clearTimeout(moveThrottleTimerRef.current);
        moveThrottleTimerRef.current = null;
      }

      if (wheelTimeoutRef.current) {
        clearTimeout(wheelTimeoutRef.current);
        wheelTimeoutRef.current = null;
      }

      disconnectDevice(true);
    };
  }, [connectDevice, disconnectDevice]);

  // ✅ 方案 1：响应 isVisible 变化
  useEffect(() => {
    if (!isVisible && socketRef.current?.connected) {
      console.log(
        `[ScrcpyPlayer] [${deviceId}] Component hidden, disconnecting stream`
      );
      // Use queueMicrotask to avoid synchronous setState within effect
      queueMicrotask(() => {
        disconnectDevice(true); // 抑制重连
      });
    } else if (
      isVisible &&
      status === 'disconnected' &&
      !socketRef.current?.connected
    ) {
      console.log(
        `[ScrcpyPlayer] [${deviceId}] Component visible again, reconnecting`
      );
      // 小延迟避免快速重连
      const timer = setTimeout(() => {
        connectDevice();
      }, 100);
      return () => clearTimeout(timer);
    }
  }, [isVisible, status, deviceId, disconnectDevice, connectDevice]);

  // 监听手动重连事件
  useEffect(() => {
    const handleReconnect = () => {
      console.log('[ScrcpyPlayer] Manual reconnect triggered');
      setStatus('connecting');
      setErrorMessage(null);
      // Small delay before reconnecting
      setTimeout(() => {
        connectDevice();
      }, 200);
    };

    window.addEventListener('scrcpy-reconnect', handleReconnect);
    return () => {
      window.removeEventListener('scrcpy-reconnect', handleReconnect);
    };
  }, [connectDevice]);

  const getStreamDimensions = () => {
    if (screenInfo) {
      return { width: screenInfo.width, height: screenInfo.height };
    }
    const canvas = canvasRef.current;
    if (canvas) {
      return { width: canvas.width, height: canvas.height };
    }
    if (deviceResolution) {
      return { width: deviceResolution.width, height: deviceResolution.height };
    }
    return null;
  };

  const mapToDeviceCoordinates = (clientX: number, clientY: number) => {
    const canvas = canvasRef.current;
    const streamDimensions = getStreamDimensions();
    if (!streamDimensions) return null;

    const rect = canvas ? canvas.getBoundingClientRect() : null;
    if (rect) {
      if (
        clientX < rect.left ||
        clientX > rect.right ||
        clientY < rect.top ||
        clientY > rect.bottom
      ) {
        return null;
      }
      const relativeX = clientX - rect.left;
      const relativeY = clientY - rect.top;
      const streamX = Math.round((relativeX / rect.width) * streamDimensions.width);
      const streamY = Math.round((relativeY / rect.height) * streamDimensions.height);
      const scaleX = deviceResolution ? deviceResolution.width / streamDimensions.width : 1;
      const scaleY = deviceResolution ? deviceResolution.height / streamDimensions.height : 1;
      return {
        x: Math.round(streamX * scaleX),
        y: Math.round(streamY * scaleY),
      };
    }

    // No canvas yet — use fallbackScreenshot image container dimensions (9:16 aspect ratio)
    const container = videoContainerRef.current;
    if (!container) return null;
    const containerRect = container.getBoundingClientRect();
    if (
      clientX < containerRect.left ||
      clientX > containerRect.right ||
      clientY < containerRect.top ||
      clientY > containerRect.bottom
    ) {
      return null;
    }
    const relativeX = clientX - containerRect.left;
    const relativeY = clientY - containerRect.top;
    const containerAspect = containerRect.width / containerRect.height;
    const deviceAspect = streamDimensions.width / streamDimensions.height;
    let drawWidth: number, drawHeight: number, offsetX: number, offsetY: number;
    if (containerAspect > deviceAspect) {
      drawHeight = containerRect.height;
      drawWidth = drawHeight * deviceAspect;
      offsetX = (containerRect.width - drawWidth) / 2;
      offsetY = 0;
    } else {
      drawWidth = containerRect.width;
      drawHeight = drawWidth / deviceAspect;
      offsetX = 0;
      offsetY = (containerRect.height - drawHeight) / 2;
    }
    if (
      clientX < containerRect.left + offsetX ||
      clientX > containerRect.left + offsetX + drawWidth ||
      clientY < containerRect.top + offsetY ||
      clientY > containerRect.top + offsetY + drawHeight
    ) {
      return null;
    }
    const imgX = clientX - (containerRect.left + offsetX);
    const imgY = clientY - (containerRect.top + offsetY);
    const scaleX = deviceResolution ? deviceResolution.width / streamDimensions.width : 1;
    const scaleY = deviceResolution ? deviceResolution.height / streamDimensions.height : 1;
    return {
      x: Math.round((imgX / drawWidth) * streamDimensions.width * scaleX),
      y: Math.round((imgY / drawHeight) * streamDimensions.height * scaleY),
    };
  };

  const handleMouseDown = async (event: MouseEvent<HTMLDivElement>) => {
    if (!enableControl || !controlEnabled) {
      console.log('[ScrcpyPlayer] Mouse down blocked:', { enableControl, controlEnabled, status });
      return;
    }

    const coords = mapToDeviceCoordinates(event.clientX, event.clientY);
    if (!coords) {
      console.log('[ScrcpyPlayer] No coords mapped for mouse down');
      return;
    }

    console.log('[ScrcpyPlayer] Touch down:', coords, 'deviceId:', deviceId);
    isDraggingRef.current = true;
    movedRef.current = false;
    dragStartRef.current = { x: event.clientX, y: event.clientY };
    swipeStartRef.current = { x: coords.x, y: coords.y };

    try {
      await sendTouchDown(coords.x, coords.y, deviceId);
    } catch (error) {
      console.error('[ScrcpyPlayer] Touch down failed:', error);
    }
  };

  const handleMouseMove = (event: MouseEvent<HTMLDivElement>) => {
    if (!isDraggingRef.current || !controlEnabled) return;

    const now = Date.now();
    const coords = mapToDeviceCoordinates(event.clientX, event.clientY);
    if (!coords) return;

    if (dragStartRef.current) {
      const dx = event.clientX - dragStartRef.current.x;
      const dy = event.clientY - dragStartRef.current.y;
      if (Math.hypot(dx, dy) > 4) {
        movedRef.current = true;
      }
    }

    pendingMoveRef.current = coords;
    if (now - lastMoveTimeRef.current < MOTION_THROTTLE_MS) {
      if (!moveThrottleTimerRef.current) {
        moveThrottleTimerRef.current = setTimeout(() => {
          moveThrottleTimerRef.current = null;
          if (pendingMoveRef.current) {
            sendTouchMove(
              pendingMoveRef.current.x,
              pendingMoveRef.current.y,
              deviceId
            ).catch(error => {
              console.error('[ScrcpyPlayer] Touch move failed:', error);
            });
            pendingMoveRef.current = null;
            lastMoveTimeRef.current = Date.now();
          }
        }, MOTION_THROTTLE_MS);
      }
      return;
    }

    lastMoveTimeRef.current = now;
    sendTouchMove(coords.x, coords.y, deviceId).catch(error => {
      console.error('[ScrcpyPlayer] Touch move failed:', error);
    });
  };

  const handleMouseUp = async (event: MouseEvent<HTMLDivElement>) => {
    if (!isDraggingRef.current || !controlEnabled) return;

    const coords = mapToDeviceCoordinates(event.clientX, event.clientY);
    isDraggingRef.current = false;
    dragStartRef.current = null;
    const swipeStart = swipeStartRef.current;
    swipeStartRef.current = null;

    if (!coords) return;

    try {
      await sendTouchUp(coords.x, coords.y, deviceId);
      if (!movedRef.current) {
        onTapSuccess?.(coords.x, coords.y);
      } else {
        onSwipeSuccess?.(swipeStart?.x ?? 0, swipeStart?.y ?? 0, coords.x, coords.y);
      }
      onControlActionRef.current?.();
    } catch (error) {
      const message = String(error);
      if (!movedRef.current) {
        onTapError?.(message);
      } else {
        onSwipeError?.(message);
      }
    }
  };

  const handleMouseLeave = async (event: MouseEvent<HTMLDivElement>) => {
    if (!isDraggingRef.current || !controlEnabled) return;

    const coords = mapToDeviceCoordinates(event.clientX, event.clientY);
    isDraggingRef.current = false;
    dragStartRef.current = null;
    swipeStartRef.current = null;

    if (!coords) return;

    try {
      await sendTouchUp(coords.x, coords.y, deviceId);
    } catch (error) {
      console.error('[ScrcpyPlayer] Touch cancel failed:', error);
    }
  };

  const handleWheel = (event: WheelEvent<HTMLDivElement>) => {
    if (!enableControl || !controlEnabled) return;

    event.preventDefault();
    const deltaY = event.deltaY;

    if (!accumulatedScrollRef.current) {
      accumulatedScrollRef.current = { deltaY: 0 };
    }
    accumulatedScrollRef.current.deltaY += deltaY;

    if (wheelTimeoutRef.current) {
      clearTimeout(wheelTimeoutRef.current);
    }

    wheelTimeoutRef.current = setTimeout(async () => {
      const current = accumulatedScrollRef.current;
      accumulatedScrollRef.current = null;
      if (!current) return;

      const streamDimensions = getStreamDimensions();
      if (!streamDimensions) return;

      // Use canvas rect if available, otherwise fall back to container rect
      const canvas = canvasRef.current;
      const container = videoContainerRef.current;
      let rect: DOMRect | null = null;
      if (canvas) {
        rect = canvas.getBoundingClientRect();
      } else if (container) {
        rect = container.getBoundingClientRect();
      }
      if (!rect) return;

      const centerX = rect.left + rect.width / 2;
      const centerY = rect.top + rect.height / 2;

      const startCoords = mapToDeviceCoordinates(centerX, centerY);
      if (!startCoords) return;

      const delta = Math.max(Math.min(current.deltaY, 600), -600);
      const endClientY = centerY + delta;
      const endCoords = mapToDeviceCoordinates(centerX, endClientY);
      if (!endCoords) return;

      try {
        const result = await sendSwipe(
          startCoords.x,
          startCoords.y,
          endCoords.x,
          endCoords.y,
          300,
          deviceId
        );
        if (result.success) {
          onSwipeSuccess?.(startCoords.x, startCoords.y, endCoords.x, endCoords.y);
          onControlActionRef.current?.();
        } else {
          onSwipeError?.(result.error || 'Scroll failed');
        }
      } catch (error) {
        onSwipeError?.(String(error));
      }
    }, WHEEL_DELAY_MS);
  };

  const handleTouchStart = async (event: React.TouchEvent<HTMLDivElement>) => {
    if (!enableControl || !controlEnabled) return;
    event.preventDefault();

    const touch = event.touches[0];
    if (!touch) return;

    const coords = mapToDeviceCoordinates(touch.clientX, touch.clientY);
    if (!coords) return;

    isDraggingRef.current = true;
    movedRef.current = false;
    dragStartRef.current = { x: touch.clientX, y: touch.clientY };
    swipeStartRef.current = { x: coords.x, y: coords.y };

    try {
      await sendTouchDown(coords.x, coords.y, deviceId);
    } catch (error) {
      console.error('[ScrcpyPlayer] Touch start failed:', error);
    }
  };

  const handleTouchMove = (event: React.TouchEvent<HTMLDivElement>) => {
    if (!isDraggingRef.current || !controlEnabled) return;
    event.preventDefault();

    const touch = event.touches[0];
    if (!touch) return;

    const now = Date.now();
    const coords = mapToDeviceCoordinates(touch.clientX, touch.clientY);
    if (!coords) return;

    if (dragStartRef.current) {
      const dx = touch.clientX - dragStartRef.current.x;
      const dy = touch.clientY - dragStartRef.current.y;
      if (Math.hypot(dx, dy) > 4) {
        movedRef.current = true;
      }
    }

    pendingMoveRef.current = coords;
    if (now - lastMoveTimeRef.current < MOTION_THROTTLE_MS) {
      if (!moveThrottleTimerRef.current) {
        moveThrottleTimerRef.current = setTimeout(() => {
          moveThrottleTimerRef.current = null;
          if (pendingMoveRef.current) {
            sendTouchMove(
              pendingMoveRef.current.x,
              pendingMoveRef.current.y,
              deviceId
            ).catch(error => {
              console.error('[ScrcpyPlayer] Touch move failed:', error);
            });
            pendingMoveRef.current = null;
            lastMoveTimeRef.current = Date.now();
          }
        }, MOTION_THROTTLE_MS);
      }
      return;
    }

    lastMoveTimeRef.current = now;
    sendTouchMove(coords.x, coords.y, deviceId).catch(error => {
      console.error('[ScrcpyPlayer] Touch move failed:', error);
    });
  };

  const handleTouchEnd = async (event: React.TouchEvent<HTMLDivElement>) => {
    if (!isDraggingRef.current || !controlEnabled) return;
    event.preventDefault();

    const touch = event.changedTouches[0];
    isDraggingRef.current = false;
    dragStartRef.current = null;
    const swipeStart = swipeStartRef.current;
    swipeStartRef.current = null;

    if (!touch) return;

    const coords = mapToDeviceCoordinates(touch.clientX, touch.clientY);
    if (!coords) return;

    try {
      await sendTouchUp(coords.x, coords.y, deviceId);
      if (!movedRef.current) {
        onTapSuccess?.(coords.x, coords.y);
      } else {
        onSwipeSuccess?.(swipeStart?.x ?? 0, swipeStart?.y ?? 0, coords.x, coords.y);
      }
      onControlActionRef.current?.();
    } catch (error) {
      const message = String(error);
      if (!movedRef.current) {
        onTapError?.(message);
      } else {
        onSwipeError?.(message);
      }
    }
  };

  // Android keycode mapping
  const KEYCODE_MAP: Record<string, number> = {
    // Navigation
    Backspace: 67,    // KEYCODE_DEL
    Delete: 112,      // KEYCODE_FORWARD_DEL
    Enter: 66,        // KEYCODE_ENTER
    Tab: 61,          // KEYCODE_TAB
    Escape: 111,      // KEYCODE_ESCAPE
    // Arrow keys
    ArrowUp: 19,      // KEYCODE_DPAD_UP
    ArrowDown: 20,    // KEYCODE_DPAD_DOWN
    ArrowLeft: 21,    // KEYCODE_DPAD_LEFT
    ArrowRight: 22,   // KEYCODE_DPAD_RIGHT
    // Function keys
    Home: 3,          // KEYCODE_HOME
    End: 123,         // KEYCODE_MOVE_END
    PageUp: 92,       // KEYCODE_PAGE_UP
    PageDown: 93,     // KEYCODE_PAGE_DOWN
    // Media
    ' ': 62,          // KEYCODE_SPACE
  };

  const handleKeyDown = async (event: React.KeyboardEvent<HTMLDivElement>) => {
    if (!enableControl || !controlEnabled) return;

    // Ctrl/Cmd combos
    if (event.ctrlKey || event.metaKey) {
      if (event.key === 'c') return; // allow copy
      if (event.key === 'v') return; // allow paste
      if (event.key === 'a') return; // allow select all
      if (event.key === 'z') return; // allow undo
    }

    // Map special keys to keycodes
    const keycode = KEYCODE_MAP[event.key];
    if (keycode) {
      event.preventDefault();
      try {
        await sendKeyEvent(keycode, deviceId);
        onTapSuccess?.(0, 0);
        onControlActionRef.current?.();
      } catch (error) {
        console.error('[ScrcpyPlayer] Key event failed:', error);
      }
      return;
    }

    // For printable characters, send as text input
    if (event.key.length === 1 && !event.ctrlKey && !event.metaKey && !event.altKey) {
      event.preventDefault();
      try {
        await sendTextInput(event.key, deviceId);
        onTapSuccess?.(0, 0);
        onControlActionRef.current?.();
      } catch (error) {
        console.error('[ScrcpyPlayer] Text input failed:', error);
      }
    }
  };

  return (
    <div
      className={`relative w-full h-full flex items-center justify-center ${className || ''}`}
    >
      <div
        ref={videoContainerRef}
        tabIndex={0}
        className="relative w-full h-full flex items-center justify-center bg-zinc-50 dark:bg-zinc-900 outline-none"
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseLeave}
        onWheel={handleWheel}
        onTouchStart={handleTouchStart}
        onTouchMove={handleTouchMove}
        onTouchEnd={handleTouchEnd}
        onKeyDown={handleKeyDown}
      >
        {/* Fallback screenshot shown when stream is not connected */}
        {fallbackScreenshot && status !== 'connected' && (
          <img
            src={`data:image/png;base64,${fallbackScreenshot}`}
            alt="Device Preview"
            className="absolute inset-0 w-full h-full object-contain pointer-events-none"
            style={{ zIndex: 0 }}
          />
        )}

        {/* Connecting / error / disconnected — show retry button only for failure states */}
        {(status === 'error' || status === 'disconnected') && (
          <div
            className="absolute inset-0 z-10 flex flex-col items-center justify-center bg-black/50"
          >
            {status === 'error' && (
              <div className="flex items-center gap-2 px-4 py-2 rounded-full bg-black/70 backdrop-blur text-white/80 text-sm">
                <AlertCircle className="w-4 h-4 text-red-400" />
                <span>{errorMessage || '连接失败'}</span>
              </div>
            )}
            {status === 'disconnected' && (
              <div className="flex items-center gap-2 px-4 py-2 rounded-full bg-black/70 backdrop-blur text-white/80 text-sm">
                <AlertCircle className="w-4 h-4" />
                <span>已断开</span>
              </div>
            )}
            <button
              onClick={() => {
                window.dispatchEvent(new CustomEvent('scrcpy-reconnect'));
              }}
              className="mt-4 px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white text-sm transition-colors"
            >
              重试连接
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
