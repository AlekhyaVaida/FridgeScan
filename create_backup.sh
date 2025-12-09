#!/bin/bash

# Backup Script for Fridge Scan Project
# This script creates a clean backup excluding regeneratable files

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PARENT_DIR="$(dirname "$SCRIPT_DIR")"
PROJECT_NAME="fridge_spoilage_detection_starter"
BACKUP_NAME="fridge_spoilage_detection_BACKUP"
BACKUP_PATH="$PARENT_DIR/$BACKUP_NAME"

echo -e "${BLUE}📦 Creating backup of $PROJECT_NAME...${NC}"
echo ""

# Check if backup already exists
if [ -d "$BACKUP_PATH" ]; then
    echo -e "${YELLOW}⚠️  Backup folder already exists!${NC}"
    read -p "Delete and recreate? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm -rf "$BACKUP_PATH"
        echo -e "${GREEN}✅ Old backup removed${NC}"
    else
        echo "Aborted."
        exit 1
    fi
fi

# Create backup directory
mkdir -p "$BACKUP_PATH"

echo -e "${BLUE}📋 Copying files (excluding node_modules, venv, __pycache__, etc.)...${NC}"

# Use rsync to copy files, excluding unnecessary directories
rsync -av \
    --exclude='node_modules' \
    --exclude='venv' \
    --exclude='__pycache__' \
    --exclude='.expo' \
    --exclude='*.pyc' \
    --exclude='.DS_Store' \
    --exclude='*.log' \
    --exclude='.git' \
    --exclude='dist' \
    --exclude='build' \
    --exclude='.next' \
    "$SCRIPT_DIR/" "$BACKUP_PATH/"

echo ""
echo -e "${GREEN}✅ Backup created successfully!${NC}"
echo ""
echo -e "${BLUE}📍 Backup location: ${BACKUP_PATH}${NC}"
echo ""
echo -e "${YELLOW}📝 Next steps:${NC}"
echo "1. Test copy: cp -r $BACKUP_PATH ${PARENT_DIR}/fridge_spoilage_detection_TEST"
echo "2. Open in VS Code: code ${PARENT_DIR}/fridge_spoilage_detection_TEST"
echo "3. Set up dependencies:"
echo "   - Backend: cd backend && python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt"
echo "   - Frontend: cd FridgeScanApp && npm install"
echo ""

