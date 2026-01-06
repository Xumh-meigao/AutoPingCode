#!/bin/bash

# ==================== 配置 ====================
OUTPUT_DIR="/root/smart_data"
TIMESTAMP=$(TZ=Asia/Shanghai date +"%Y%m%dT%H%M%S")
mkdir -p "$OUTPUT_DIR"
OUTPUT_FILE="$OUTPUT_DIR/smart_system_disk_$TIMESTAMP.json"
# ==============================================

# 获取根文件系统所在设备
root_dev=$(df / 2>/dev/null | awk 'NR==2 {print $1}')

if [ -z "$root_dev" ]; then
    echo "❌ 无法获取根文件系统设备"
    exit 1
fi

# 提取物理磁盘设备名（去除分区后缀）
case "$root_dev" in
    /dev/ada[0-9]*)
        SYSTEM_DISK="/dev/$(echo "$root_dev" | sed -E 's@/dev/(ada[0-9]+)p[0-9]*@\1@')"
        ;;
    /dev/nvme[0-9]*n[0-9]*)
        SYSTEM_DISK="/dev/$(echo "$root_dev" | sed -E 's@/dev/(nvme[0-9]+n[0-9]+)p[0-9]*@\1@')"
        ;;
    /dev/sd[a-z]*|/dev/hd[a-z]*)
        SYSTEM_DISK="/dev/$(echo "$root_dev" | sed -E 's@/dev/([a-z]+)[0-9]*@\1@')"
        ;;
    *)
        # 通用兜底：移除结尾数字（适用于如 /dev/vda1, /dev/mmcblk0p1 等）
        SYSTEM_DISK=$(echo "$root_dev" | sed 's/[0-9]*$//')
        ;;
esac

# 验证是否成功提取
if [ -z "$SYSTEM_DISK" ] || [ "$SYSTEM_DISK" = "/dev/" ]; then
    echo "❌ 无法解析系统磁盘设备：$root_dev"
    exit 1
fi

echo "检测到系统盘: $SYSTEM_DISK"

# 检查 smartctl 是否已安装
if ! command -v smartctl >/dev/null 2>&1; then
    echo "❌ smartctl 未安装，请运行：sudo apt install smartmontools"
    exit 1
fi

# 获取 SMART JSON 数据
echo "正在获取 SMART 数据（JSON 格式）..."
if smartctl -j -a "$SYSTEM_DISK" > "$OUTPUT_FILE"; then
    echo "✅ SMART 数据已保存到: $OUTPUT_FILE"
else
    echo "❌ smartctl 命令失败，请确认设备支持 SMART 并已启用"
    exit 1
fi

:<<!
sudo tee /etc/systemd/system/smart-monitor.service <<'EOF'
[Unit]
Description=Collect SMART data from system disk
After=network.target

[Service]
Type=oneshot
User=root
ExecStart=/usr/local/bin/get_smart_system_disk.sh
StandardOutput=journal
StandardError=journal
EOF
!


:<<!
sudo tee /etc/systemd/system/smart-monitor.timer <<'EOF'
[Unit]
Description=Run SMART data collection daily at 09:00 and 19:00
Requires=smart-monitor.service

[Timer]
OnCalendar=*-*-* 09:00:00
OnCalendar=*-*-* 19:00:00
Persistent=true

[Install]
WantedBy=timers.target
EOF
!

:<<!
systemctl daemon-reload
systemctl enable --now smart-monitor.timer
systemctl list-timers smart-monitor.timer
systemctl restart smart-monitor.timer
!
