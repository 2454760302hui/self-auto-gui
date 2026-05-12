import time
import subprocess
import os
import sys
import json
import threading

# 程序名配置
radName = "rad_windows_amd64.exe"
xrayName = "xray_windows_amd64.exe"
xrayProxy = "127.0.0.1:7777"

def check_files_exist():
    """检查必要的程序文件是否存在"""
    missing_files = []
    if not os.path.exists(radName):
        missing_files.append(radName)
    if not os.path.exists(xrayName):
        missing_files.append(xrayName)
    if not os.path.exists("target.txt"):
        missing_files.append("target.txt")
    
    if missing_files:
        print(f"错误：以下文件不存在: {', '.join(missing_files)}")
        print("请确保所有程序文件都在当前目录下")
        sys.exit(1)

def start_xray():
    """启动xray监听"""
    outputPath = time.strftime("%Y%m%d%H%M%S", time.localtime())
    json_output = f"{outputPath}.json"
    html_output = f"{outputPath}.html"
    
    cmd = [xrayName, "webscan", "--listen", xrayProxy, 
           "--html-output", html_output, "--json-output", json_output]
    
    try:
        subprocess.Popen(cmd, creationflags=subprocess.CREATE_NEW_CONSOLE)
        print(f"Xray已启动，监听地址: {xrayProxy}")
        print(f"扫描结果将保存到: {html_output} 和 {json_output}")
        return outputPath
    except Exception as e:
        print(f"启动Xray时出错: {e}")
        return None

def scan_target(target):
    """扫描单个目标"""
    cmd = [radName, "-t", target, "-http-proxy", xrayProxy]
    try:
        print(f"正在扫描: {target}")
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()
        
        if process.returncode == 0:
            print(f"✓ 扫描完成: {target}")
        else:
            print(f"✗ 扫描失败: {target} - {stderr.decode('utf-8', errors='ignore')}")
            
    except Exception as e:
        print(f"扫描 {target} 时出错: {e}")

def main():
    # 检查文件是否存在
    check_files_exist()
    
    # 启动xray
    output_file = start_xray()
    if not output_file:
        return
    
    # 等待xray启动
    print("等待Xray启动...")
    time.sleep(5)
    
    # 读取目标文件并扫描
    try:
        with open("target.txt", "r", encoding="utf-8") as f:
            targets = [line.strip() for line in f if line.strip()]
        
        if not targets:
            print("target.txt 文件为空或没有有效目标")
            return
            
        print(f"共找到 {len(targets)} 个目标")
        
        for i, target in enumerate(targets, 1):
            print(f"\n[{i}/{len(targets)}] 开始扫描目标")
            scan_target(target)
            
            # 扫描间隔
            if i < len(targets):
                time.sleep(3)
        
        # 等待扫描完成
        print("\n等待扫描结果生成...")
        time.sleep(10)
        
        print(f"\n✅ 所有目标扫描完成！")
        print(f"📊 扫描报告: {output_file}.html")
        print(f"📄 JSON结果: {output_file}.json")
        
    except Exception as e:
        print(f"扫描过程中出错: {e}")

if __name__ == "__main__":
    main()

