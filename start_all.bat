@echo off
setlocal EnableDelayedExpansion

echo Iniciando todos los servicios de Kafka-Bitcoin-Tracker...

:: Cargar variables desde el archivo .env
for /f "tokens=1,2 delims==" %%a in (.env) do (
    set %%a=%%b
)

:: Guardar el directorio actual (donde están producer.py y consumer.py)
set "PROJECT_DIR=%CD%"

:: Cambiar al directorio de Kafka
cd /d %KAFKA_DIR%
if errorlevel 1 (
    echo Error: No se pudo cambiar al directorio %KAFKA_DIR%
    pause
    exit /b 1
)

:: Iniciar Zookeeper en una nueva ventana
start "Zookeeper" cmd /k !ZOOKEEPER_START! !ZOOKEEPER_CONFIG!
echo Iniciando Zookeeper...
timeout /t 5 >nul

:: Iniciar Kafka Server en una nueva ventana
start "Kafka Server" cmd /k !KAFKA_START! !KAFKA_CONFIG!
echo Iniciando Kafka Server...
timeout /t 10 >nul

:: Volver al directorio del proyecto para iniciar producer y consumer
cd /d %PROJECT_DIR%

:: Iniciar el Producer en una nueva ventana
start "Producer" cmd /k python !PRODUCER_PATH!
echo Iniciando Producer...
timeout /t 2 >nul

:: Iniciar el Consumer en una nueva ventana
start "Consumer" cmd /k python !CONSUMER_PATH!
echo Iniciando Consumer...

echo Todos los servicios han sido iniciados. Presiona cualquier tecla para salir.
pause