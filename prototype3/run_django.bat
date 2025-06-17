@echo off
REM 1) Django 프로젝트 폴더로 이동
cd /d "C:\kivyapp_doc_auto\prototype3"

REM 2) Conda 환경 활성화 (환경 이름을 실제 이름으로 넣어주세요)
call conda activate 

REM 3) Django 개발 서버를 백그라운드에서 실행 (출력은 모두 버림)
start "" /B python manage.py runserver 8100 > NUL 2>&1

REM 4) 서버가 기동할 시간을 잠시 대기 (5초)
timeout /t 0.5 /nobreak >nul

REM 5) 크롬으로 접속
start "" "C:\Program Files\Google\Chrome\Application\chrome.exe" http://127.0.0.1:8100

exit /b

