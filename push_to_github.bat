@echo off
chcp 65001 >nul
echo 正在推送到 https://github.com/mingxin1a/paas-platform
echo 若提示输入密码，请使用 GitHub Personal Access Token（不是登录密码）
echo 创建 Token: https://github.com/settings/tokens 勾选 repo
echo.
cd /d "%~dp0"
git push -u origin main
if errorlevel 1 (
  echo.
  echo 若因「历史不一致」被拒绝，可执行强制推送（会覆盖远程）:
  echo   git push -u origin main --force
)
pause
