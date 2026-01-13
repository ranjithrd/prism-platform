#!/bin/bash
# Install bpftrace inside eadb environment
# Called by bpftrace_install.py
# Set EADB_DEVICE environment variable to target a specific device

set -e  # Exit on error

echo "Starting bpftrace installation..."

# Ensure eadb is installed
if ! command -v eadb &> /dev/null; then
    echo "Error: eadb not found. Please install eadb first."
    exit 1
fi

# Build the eadb command with optional serial
SERIAL_ARG=""
if [ -n "$EADB_DEVICE" ]; then
    SERIAL_ARG="--serial $EADB_DEVICE"
    echo "Installing for device: $EADB_DEVICE"
else
    echo "Installing for default/first connected device"
fi
echo ""

echo "Starting installation..."

# Run all installation commands inside the eadb environment
# Pass commands via stdin to eadb shell
eadb $SERIAL_ARG shell << 'EOF'
set -e  # Exit on error inside the eadb shell too

echo "Updating package sources..."
sed -i 's/ftp.us.debian.org/deb.debian.org/g' /etc/apt/sources.list 2>/dev/null || true
grep -q "deb http://cloudfront.debian.net/debian sid main" /etc/apt/sources.list || echo "deb http://cloudfront.debian.net/debian sid main" >> /etc/apt/sources.list

echo "Updating package lists..."
apt -o Acquire::ForceIPv4=true update

echo "Installing bpftrace and dependencies..."
apt -o Acquire::ForceIPv4=true install -y bpftrace 
apt -o Acquire::ForceIPv4=true install -y bpfcc-tools libbpfcc libbpfcc-dev
apt -o Acquire::ForceIPv4=true install -y linux-headers-arm64 linux-libc-dev

echo "Linking kernel headers..."
linux_header_dirs=(/usr/src/linux-headers*-arm64)
if [ ${#linux_header_dirs[@]} -gt 0 ] && [ -d "${linux_header_dirs[0]}" ]; then
    MATCHING_LINUX_HEADER_DIR="${linux_header_dirs[0]}"
    mkdir -p /lib/modules/$(uname -r)
    ln -sf "$MATCHING_LINUX_HEADER_DIR" /lib/modules/$(uname -r)/build
    echo "Kernel headers linked successfully"
else
    echo "Warning: No kernel headers found, bpftrace may have limited functionality"
fi

echo "Creating asm header symlink..."
ln -sf /usr/include/aarch64-linux-gnu/asm /usr/include/asm
echo "ASM headers symlink created successfully"

echo "bpftrace installation complete!"
echo "Environment variables BPFTRACE_BTF and BPFTRACE_CFLAGS are set automatically during trace execution."
EOF

echo ""
echo "Installation finished successfully!"