ECHO "Building MusiGui from source wuth pyinstaller"

nuitka src\main.py --standalone --enable-plugin=pyside6 --nofollow-import-to=yt_dlp.extractor.lazy_extractors --output-filename=MusiGui.exe --output-dir=compile --windows-console-mode=disable --windows-icon-from-ico=src\assets\musigui.ico

ECHO "Copying assets folder from source to dist"

xcopy "src\assets" "compile\main.dist\assets" /s /i

ECHO "Rename main.dist to musigui"

ren "compile\main.dist" "compile\musigui"

ECHO "Compressing build"

tar.exe -a -cf compile/musigui-v0.0.0.zip compile/musigui/*

ECHO "Build zipped"

pause