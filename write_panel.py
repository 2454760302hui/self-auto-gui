import pathlib, textwrap

TARGET = pathlib.Path("frontend/src/components/QuickControlPanel.tsx")

CONTENT = textwrap.dedent('''\
import React, { useState, useCallback, useRef, useEffect } from "react";
import {
  ArrowLeft, ArrowUp, ArrowDown, ArrowLeftIcon, ArrowRightIcon,
  Home, Copy, ClipboardPaste, ListChecks, Trash2, Loader2,
  Camera, FileSearch, Smartphone, Zap, CirclePlay, CircleStop,
  Play, Search, X, Film, Monitor, MousePointerClick,
  Volume2, VolumeX, Power, Menu, CornerDownLeft, RefreshCw,
  Clipboard, Hand, ScanLine, AppWindow, Layers,
  BellOff, ChevronUp, ChevronDown,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import {
  sendBack, sendHome, sendDoubleTap, sendLongPress, sendClearText,
  sendScroll, getControlScreenshot, getUiDump, getCurrentApp,
  getClipboard, sendPaste, sendSelectAll, sendLaunchApp,
  sendKeyEvent, sendTap, sendSwipe, getInstalledApps,
  runPytest, generateGif,
  type ScreenshotControlResponse, type UiDumpResponse,
  type InstalledAppsResponse, type InstalledAppInfo, type PytestRunResponse,
} from "../api";
import { ImagePreview } from "@/components/ui/image-preview";
''')

TARGET.write_text(CONTENT, encoding="utf-8")
print(f"Written {len(CONTENT)} chars")
