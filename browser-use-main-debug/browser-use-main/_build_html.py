"""生成完整的 webui/index.html"""
import os

PARTS = []

# ── CSS ──────────────────────────────────────────────────────────────────────
PARTS.append("""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Self - Browser Use</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#f0f0f5;color:#222;min-height:100vh}
.topbar{display:flex;align-items:center;justify-content:space-between;padding:10px 24px;background:#fff;border-bottom:1px solid #e8e8e8;position:sticky;top:0;z-index:100;box-shadow:0 1px 4px rgba(0,0,0,.06)}
.logo{display:flex;align-items:center}
.llm-badge{background:#e6f9f0;color:#1a9e5c;border:1px solid #a8e6c8;border-radius:20px;padding:4px 14px;font-size:13px;font-weight:600}
.llm-badge.warn{background:#fff8e1;color:#e65100;border-color:#ffcc80}
.main{max-width:900px;margin:24px auto;padding:0 16px}
.card,.model-card,.history-card{background:#fff;border-radius:12px;box-shadow:0 1px 8px rgba(0,0,0,.08);padding:22px;margin-bottom:18px}
.card-title{font-size:15px;font-weight:700;margin-bottom:16px;display:flex;align-items:center;gap:7px}
.tabs{display:flex;border-radius:10px;overflow:hidden;border:1px solid #e0e0e0;margin-bottom:18px}
.tab{flex:1;padding:11px;text-align:center;cursor:pointer;font-size:14px;font-weight:600;background:#f8f8f8;border:none;transition:all .2s;display:flex;align-items:center;justify-content:center;gap:6px}
.tab.active{background:#7c3aed;color:#fff}
.tab:not(.active):hover{background:#f0eeff;color:#7c3aed}
.llm-info-box{background:#f0eeff;border:1px solid #d4c5ff;border-radius:10px;padding:14px 16px;margin-bottom:14px;font-size:13.5px;line-height:1.8;color:#3d1f8a}
.llm-info-box .row{display:flex;align-items:flex-start;gap:8px;margin-bottom:4px}
.llm-demo-row{display:flex;flex-wrap:wrap;gap:6px;margin-top:8px;align-items:center}
.llm-demo-label{font-weight:700;color:#3d1f8a;font-size:13px;flex-shrink:0}
.llm-demo-btn{padding:4px 10px;border-radius:5px;border:1px solid #c4b0ff;background:#fff;cursor:pointer;font-size:12px;color:#5b21b6;transition:all .15s}
.llm-demo-btn:hover{background:#7c3aed;color:#fff;border-color:#7c3aed}
.llm-task{width:100%;padding:11px 13px;border:1px solid #ddd;border-radius:8px;font-size:14px;outline:none;min-height:90px;resize:vertical;line-height:1.6}
.llm-task:focus{border-color:#7c3aed}
.nlp-info{background:#eef4ff;border:1px solid #c7d9ff;border-radius:10px;padding:13px 16px;margin-bottom:14px;font-size:13px;line-height:1.7;color:#2d4a8a}
.nlp-info b{color:#1a2e6b}
.demo-row{display:flex;flex-wrap:wrap;gap:6px;margin-top:9px;align-items:center}
.demo-label{font-weight:700;color:#333;font-size:13px;flex-shrink:0}
.demo-btn{padding:4px 10px;border-radius:5px;border:1px solid #ddd;background:#fff;cursor:pointer;font-size:12px;color:#444;transition:all .15s}
.demo-btn:hover{background:#7c3aed;color:#fff;border-color:#7c3aed}
.doc-btn{padding:4px 13px;border-radius:5px;background:#7c3aed;color:#fff;border:none;cursor:pointer;font-size:12px;font-weight:600}
.record-box{background:#f0fff4;border:1px solid #b2e8cc;border-radius:10px;padding:14px 16px;margin-bottom:14px}
.record-title{font-size:13.5px;font-weight:700;color:#1a6e3c;margin-bottom:10px;display:flex;align-items:center;gap:6px}
.record-row{display:flex;gap:9px}
.record-input{flex:1;padding:9px 13px;border:1px solid #ccc;border-radius:7px;font-size:13.5px;outline:none}
.record-input:focus{border-color:#1a9e5c}
.record-btn{padding:9px 18px;background:#1a9e5c;color:#fff;border:none;border-radius:7px;cursor:pointer;font-size:13.5px;font-weight:600;white-space:nowrap}
.record-btn:hover{background:#157a48}
.nlp-header{display:flex;justify-content:space-between;align-items:center;margin-bottom:7px}
.nlp-label{font-size:13.5px;color:#666}
.nlp-actions{display:flex;gap:7px}
.action-btn{padding:4px 11px;border-radius:5px;border:1px solid #ddd;background:#fff;cursor:pointer;font-size:12.5px;color:#555;display:flex;align-items:center;gap:4px}
.action-btn:hover{background:#f0eeff;border-color:#7c3aed;color:#7c3aed}
textarea{width:100%;border:1px solid #ddd;border-radius:8px;padding:11px 12px;font-size:13.5px;font-family:monospace;resize:vertical;outline:none;min-height:150px;line-height:1.7}
textarea:focus{border-color:#7c3aed}
.cheatsheet{background:#fffbf0;border:1px solid #ffe0a0;border-radius:10px;padding:13px 16px;margin-top:13px;font-size:12.5px}
.cheatsheet b{color:#7c4a00;display:block;margin-bottom:7px;font-size:13px}
.cheat-line{color:#555;margin-bottom:5px;line-height:1.6}
.cheat-line span{color:#7c3aed;font-weight:600}
.btn-row{display:flex;gap:10px;margin-top:15px;flex-wrap:wrap;align-items:center}
.btn-exec{padding:11px 26px;background:#7c3aed;color:#fff;border:none;border-radius:9px;cursor:pointer;font-size:14px;font-weight:700;display:flex;align-items:center;gap:7px;transition:all .2s}
.btn-exec:hover{background:#6d28d9}
.btn-exec:disabled{background:#bbb;cursor:not-allowed}
.btn-secondary{padding:11px 18px;background:#fff;color:#555;border:1px solid #ddd;border-radius:9px;cursor:pointer;font-size:13.5px;font-weight:600;display:flex;align-items:center;gap:5px}
.btn-secondary:hover{background:#f5f5f5}
.model-header{display:flex;align-items:center;justify-content:space-between;cursor:pointer}
.model-title,.history-title{font-size:15px;font-weight:700;display:flex;align-items:center;gap:7px}
.model-arrow{font-size:14px;color:#999;transition:transform .2s}
.model-arrow.open{transform:rotate(90deg)}
.model-body{margin-top:14px;display:none}
.model-body.open{display:block}
.model-ok{color:#1a9e5c;font-size:13px;font-weight:600;margin-top:8px}
.model-ok a{color:#1a9e5c}
.model-form{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:12px}
.model-field label{display:block;font-size:12px;color:#888;margin-bottom:4px}
.model-field input{width:100%;padding:8px 11px;border:1px solid #ddd;border-radius:6px;font-size:13px;outline:none}
.model-field input:focus{border-color:#7c3aed}
.model-field.full{grid-column:1/-1}
.history-header{display:flex;align-items:center;justify-content:space-between;margin-bottom:14px}
.history-actions{display:flex;gap:8px}
.btn-sm{padding:5px 13px;border-radius:6px;border:1px solid #ddd;background:#fff;cursor:pointer;font-size:12.5px;color:#555;font-weight:600}
.btn-sm:hover{background:#f5f5f5}
.btn-sm.danger{border-color:#ffb3b3;color:#c0392b}
.btn-sm.danger:hover{background:#fff5f5}
.history-list{max-height:340px;overflow-y:auto}
.history-item{padding:11px 14px;border:1px solid #eee;border-radius:8px;margin-bottom:8px;cursor:pointer;transition:all .15s}
.history-item:hover{border-color:#c4b0ff;background:#faf8ff}
.history-item .task-text{font-size:13.5px;color:#333;margin-bottom:5px;font-weight:500;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.history-item .meta{display:flex;align-items:center;gap:8px;font-size:12px;color:#999}
.badge{padding:2px 8px;border-radius:4px;font-size:11.5px;font-weight:700}
.badge.pass{background:#e6f9f0;color:#1a9e5c}
.badge.fail{background:#ffe8e8;color:#c0392b}
.gif-link{color:#7c3aed;text-decoration:none;font-size:12px}
.gif-link:hover{text-decoration:underline}
.result-box{margin-top:14px;background:#f8f8f8;border:1px solid #e0e0e0;border-radius:10px;padding:14px;font-size:13px;font-family:monospace;white-space:pre-wrap;max-height:300px;overflow-y:auto;display:none;line-height:1.6}
.result-box.show{display:block}
.result-box.success{border-color:#b2e8cc;background:#f0fff4}
.result-box.error{border-color:#ffb3b3;background:#fff5f5}
.spinner{display:inline-block;width:14px;height:14px;border:2px solid rgba(255,255,255,.4);border-top-color:#fff;border-radius:50%;animation:spin .7s linear infinite}
@keyframes spin{to{transform:rotate(360deg)}}
.modal{display:none;position:fixed;inset:0;background:rgba(0,0,0,.45);z-index:200;align-items:flex-start;justify-content:center;padding-top:30px;overflow-y:auto}
.modal.show{display:flex}
.modal-box{background:#fff;border-radius:14px;padding:26px;width:92%;max-width:860px;max-height:88vh;overflow-y:auto;position:relative;margin-bottom:30px}
.modal-title{font-size:16px;font-weight:700;margin-bottom:4px;padding-right:60px}
.modal-subtitle{font-size:13px;color:#888;margin-bottom:18px}
.modal-close{position:absolute;top:18px;right:20px;cursor:pointer;font-size:13px;color:#666;background:#f0f0f0;border:none;border-radius:6px;padding:4px 10px;font-weight:600}
.modal-close:hover{background:#e0e0e0}
.doc-section{margin-bottom:24px}
.doc-section-title{font-size:14px;font-weight:700;color:#7c3aed;margin-bottom:10px;padding-bottom:6px;border-bottom:2px solid #f0eeff;display:flex;align-items:center;gap:6px}
.doc-table{width:100%;border-collapse:collapse;font-size:13px}
.doc-table th{text-align:left;padding:7px 10px;background:#f8f8f8;color:#666;font-weight:600;border-bottom:1px solid #eee}
.doc-table td{padding:7px 10px;border-bottom:1px solid #f5f5f5;vertical-align:top}
.doc-table tr:hover td{background:#faf8ff}
.doc-table td:first-child{color:#7c3aed;font-weight:600;font-family:monospace;white-space:nowrap;width:190px}
.doc-table td:nth-child(2){color:#888;font-family:monospace;font-size:12px;width:210px}
.doc-table td:nth-child(3){color:#555}
.doc-table td:last-child{width:70px;text-align:center}
.use-btn{padding:3px 10px;border-radius:4px;border:1px solid #c4b0ff;background:#f8f5ff;cursor:pointer;font-size:11.5px;color:#7c3aed;white-space:nowrap}
.use-btn:hover{background:#7c3aed;color:#fff}
.export-preview{width:100%;min-height:280px;padding:12px;border:1px solid #ddd;border-radius:8px;font-family:monospace;font-size:12.5px;background:#f8f8f8;resize:vertical;outline:none}
.export-actions{display:flex;gap:10px;margin-top:12px}
.param-row,.adv-row{margin-bottom:12px}
.param-row label,.adv-row label{display:block;font-size:13px;color:#666;margin-bottom:4px}
.param-row input,.adv-row input{width:100%;padding:8px 11px;border:1px solid #ddd;border-radius:6px;font-size:13.5px;outline:none}
.param-row input:focus,.adv-row input:focus{border-color:#7c3aed}
</style>
</head>
<body>""")
