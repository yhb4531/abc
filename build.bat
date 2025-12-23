@echo off
chcp 65001 > nul
echo [AudioDriver] 스마트 빌드를 시작합니다...

:: 1. dist 폴더만 지웁니다. (결과물 초기화)
:: [중요] build 폴더는 지우지 않습니다! (캐시 유지 -> 속도 향상)
if exist dist rmdir /s /q dist

:: 2. 빌드 실행
:: --console을 --windowed로 바꿨습니다. (검은 창 숨김 -> 스텔스 필수)
:: --name을 "AudioDriver"로 바꿨습니다.
python -m PyInstaller --noconfirm --onedir --windowed --name "AudioDriver" --collect-all ultralytics main.py

echo.
echo [System] 빌드 완료! 데이터 폴더를 복사합니다...

:: 3. 데이터 복사 (경로를 AudioDriver로 맞춤)
xcopy /E /I /Y "models" "dist\AudioDriver\models"
xcopy /E /I /Y "data" "dist\AudioDriver\data"

echo.
echo [System] USB 이동용 압축파일을 생성합니다... (잠시만 기다리세요)

:: 4. [핵심] 자동으로 압축하기 (이름을 AudioDriver.zip으로 변경)
powershell Compress-Archive -Path "dist\AudioDriver" -DestinationPath "dist\AudioDriver.zip" -Force

echo.
echo [Success] 모든 작업 완료!
echo [Tip] USB에는 'dist\AudioDriver.zip' 파일 하나만 넣으세요!
pause