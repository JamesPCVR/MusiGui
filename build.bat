@ECHO OFF

ECHO "Building MusiGui from source with nuitka"

nuitka src\main.py --standalone --enable-plugin=pyside6 --nofollow-import-to=yt_dlp.extractor.lazy_extractors --output-filename=MusiGui.exe --output-dir=compile --windows-console-mode=disable --windows-icon-from-ico=src\assets\musigui.ico

ECHO "Copying assets folder from source to dist"

xcopy "src\assets" "compile\main.dist\assets" /s /i

ECHO "Rename main.dist to musigui"

cd compile
ren "main.dist" "musigui"

ECHO "Compressing build"

tar.exe -a -cf musigui-v0.0.0.zip musigui/*

ECHO "Build zipped"

PAUSE
cmd /k