@echo off
setlocal EnableDelayedExpansion    
IF "%LANG%"=="" (
    FOR /F "delims==" %%A IN ('systeminfo.exe ^| findstr ";"') DO  (
        FOR /F "usebackq tokens=2-3 delims=:;" %%B IN (`echo %%A`) DO (
            FOR /F "usebackq tokens=1 delims= " %%D IN (`echo %%B`) DO (
                SET LANG=%%D_ES.UTF-8
            )
        )
        GOTO :RUN
    )
)
:RUN
docker pull egofer/catatom2osm
docker run --rm -it -e LANG=%LANG% -v %cd%:/catastro egofer/catatom2osm catatom2osm %*
