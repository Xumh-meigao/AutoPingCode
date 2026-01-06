#!/usr/bin/env python3
import subprocess
import sqlite3
import json
from datetime import datetime, timezone


def init_db(db_path):
    """初始化数据库，新增 GB 字段"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS smart_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nas_ip TEXT NOT NULL,
            device TEXT NOT NULL,
            smart_json TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            data_units_read_gb REAL,      -- 新增
            data_units_written_gb REAL    -- 新增
        )
    ''')
    conn.commit()
    conn.close()

def extract_data_units_gb(smart_dict):
    """
    从 smartctl -j 的 JSON 输出中提取 Data Units 并换算为 GB（十进制）
    返回: (read_gb, written_gb) 或 (None, None)
    """
    try:
        # NVMe 设备的数据在 nvme_smart_health_information_log 下
        health_log = smart_dict.get("nvme_smart_health_information_log")
        if not health_log:
            return None, None

        read_units = health_log.get("data_units_read")
        write_units = health_log.get("data_units_written")

        if read_units is None or write_units is None:
            return None, None

        # 换算：1 unit = 512,000 bytes; 1 GB = 1e9 bytes
        read_gb = read_units * 512 / 1_000_000
        write_gb = write_units * 512 / 1_000_000

        return round(read_gb, 2), round(write_gb, 2)
    except (TypeError, KeyError, ValueError):
        return None, None


def get_nas_smart_as_dict(nas_ip, nas_user, nas_password=None, timeout=60):
    """
    通过 SSH 获取 NAS 磁盘的 SMART 信息，并返回 Python dict（使用 smartctl -j）
    
    返回:
        (device: str, smart_dict: dict) 或 (None, None)
    """
    print(f"正在连接 NAS ({nas_ip}) 并检测系统盘...")

    # 设备检测脚本（同前）
    detect_script = r'''
root_dev=$(df / 2>/dev/null | awk 'NR==2 {print $1}')
case "$root_dev" in
    /dev/ada[0-9]*) echo "/dev/$(echo "$root_dev" | sed -E 's@/dev/(ada[0-9]+)p[0-9]*@\1@')" ;;
    /dev/nvme[0-9]*n[0-9]*) echo "/dev/$(echo "$root_dev" | sed -E 's@/dev/(nvme[0-9]+n[0-9]+)p[0-9]*@\1@')" ;;
    /dev/sd[a-z]*|/dev/hd[a-z]*) echo "/dev/$(echo "$root_dev" | sed -E 's@/dev/([a-z]+)[0-9]*@\1@')" ;;
    *) echo "$root_dev" | sed 's/[0-9]*$//' ;;
esac
'''

    # 构建 SSH 命令（支持密码）
    if nas_password:
        ssh_cmd = ["sshpass", "-p", nas_password, "ssh", "-o", "StrictHostKeyChecking=no"]
    else:
        ssh_cmd = ["ssh", "-o", "StrictHostKeyChecking=no"]

    try:
        # 获取设备名
        cmd = ssh_cmd + [f"{nas_user}@{nas_ip}", detect_script]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        if result.returncode != 0:
            print(f"❌ 设备检测失败: {result.stderr}")
            return None, None

        lines = [l.strip() for l in result.stdout.splitlines() if l.strip()]
        remote_disk = None
        for line in reversed(lines):
            if line.startswith("/dev/"):
                remote_disk = line
                break
        if not remote_disk:
            print("❌ 未检测到有效设备")
            return None, None

        print(f"检测到设备: {remote_disk}")

        # 使用 smartctl -j 获取 JSON 格式输出（关键！）
        json_cmd = f"sudo smartctl -j -a '{remote_disk}'"
        cmd = ssh_cmd + [f"{nas_user}@{nas_ip}", json_cmd]
        smart_result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)

        if smart_result.returncode != 0:
            print(f"❌ smartctl 执行失败: {smart_result.stderr}")
            return None, None

        try:
            smart_dict = json.loads(smart_result.stdout)
            # 验证是否为有效 SMART JSON
            if "smartctl_version" in smart_dict or "device" in smart_dict:
                return remote_disk, smart_dict
            else:
                print("❌ 返回内容不是有效 SMART JSON")
                return None, None
        except json.JSONDecodeError as e:
            print(f"❌ JSON 解析失败: {e}")
            print("输出预览:", smart_result.stdout[:200])
            return None, None

    except Exception as e:
        print(f"❌ 异常: {e}")
        return None, None


def save_smart_dict_to_db(db_path, nas_ip, device, smart_dict):
    """保存 SMART JSON + 计算后的 GB 值"""
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    smart_json = json.dumps(smart_dict, ensure_ascii=False)

    read_gb, write_gb = extract_data_units_gb(smart_dict)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO smart_records (
            nas_ip, device, smart_json, timestamp,
            data_units_read_gb, data_units_written_gb
        ) VALUES (?, ?, ?, ?, ?, ?)
    ''', (nas_ip, device, smart_json, timestamp, read_gb, write_gb))
    conn.commit()
    record_id = cursor.lastrowid
    conn.close()
    return record_id


def fetch_and_store_smart_json(nas_ip, nas_user, nas_password=None, db_path=None):
    """主函数：获取 SMART JSON 并存入 DB"""
    if db_path is None:
        db_path = "/Users/test/Minis/MyScripts/AutoPingCode/data/nas_smart.db"
    init_db(db_path)
    device, smart_dict = get_nas_smart_as_dict(nas_ip, nas_user, nas_password)
    if device and smart_dict:
        record_id = save_smart_dict_to_db(db_path, nas_ip, device, smart_dict)
        print(f"✅ 完整 SMART 数据已存入 DB (ID: {record_id})")
        return record_id
    else:
        print("❌ 获取 SMART 数据失败")
        return None


# ===== 命令行入口 =====
if __name__ == "__main__":
    # if len(sys.argv) < 3:
    #     print("用法: python3 nas_smart_json.py <NAS_IP> <USER> [PASSWORD]")
    #     sys.exit(1)
    #
    # ip = sys.argv[1]
    # user = sys.argv[2]
    # password = sys.argv[3] if len(sys.argv) > 3 else None

    fetch_and_store_smart_json("192.168.1.66", "root")