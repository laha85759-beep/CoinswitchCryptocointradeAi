@echo off
title CK Capital MT5 EC2 Bridge Server
echo ==============================================================
echo Starting CK Capital Prop Firm MT5 Bridge for AWS EC2
echo Account: 116810 ^| Server: Alphaglobalmarket-live
echo MLL Floor: $9,500.00 ^| Max Daily Loss: $300.00
echo ==============================================================

:: Check python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Python not found! Please install Python 3.10+ and add to PATH.
    pause
    exit /b 1
)

:: Install prerequisites if needed
pip install MetaTrader5 Flask requests >nul 2>&1

:: Run bridge server
python ec2_mt5_bridge.py
pause
