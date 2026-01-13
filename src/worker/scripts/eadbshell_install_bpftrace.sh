#!/bin/bash
# Install bpftrace inside eadb Debian environment
# This script is designed to run INSIDE the eadb shell
# Based on verified working installation steps

set -e

# Set PATH explicitly since /data/eadb/run-command doesn't source shell init files
export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

echo "=== Installing bpftrace in eadb environment ==="

# Fix Debian mirror
echo "Fixing Debian sources..."
sed -i 's/ftp.us.debian.org/deb.debian.org/g' /etc/apt/sources.list

# Update package lists
echo "Updating package lists..."
apt -o Acquire::ForceIPv4=true update

# Install bpftrace
echo "Installing bpftrace..."
apt -o Acquire::ForceIPv4=true install -y bpftrace 

# Add sid repository for newer packages
echo "Adding Debian sid repository..."
grep -q "sid main" /etc/apt/sources.list || echo "deb http://cloudfront.debian.net/debian sid main" >> /etc/apt/sources.list

# Install BPF tools and dependencies
echo "Installing BPF tools and libraries..."
apt -o Acquire::ForceIPv4=true install -y bpfcc-tools libbpfcc libbpfcc-dev

# Install kernel headers
echo "Installing kernel headers..."
apt -o Acquire::ForceIPv4=true install -y linux-headers-arm64 linux-libc-dev

# NOTE: Do NOT symlink Debian kernel headers to Android kernel version
# The Debian headers are incompatible with Android kernel
# bpftrace will work without kernel headers by using BTF data from /sys/kernel/btf/vmlinux
# which is accessible when running on the Android side (not from eadb chroot)

# Create asm symlink for header includes
echo "Creating asm header symlink..."
ln -sf /usr/include/aarch64-linux-gnu/asm /usr/include/asm

echo ""
echo "=== bpftrace installation complete! ==="
echo ""
echo "Environment variables are set automatically during trace execution:"
echo "  BPFTRACE_BTF=/sys/kernel/btf/vmlinux"
echo "  BPFTRACE_CFLAGS=\"-I/usr/include/aarch64-linux-gnu\""
