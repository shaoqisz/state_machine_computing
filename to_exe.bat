pyinstaller -F -w state_machine_ui.py  -i="sm.ico" -n state_machine_computing --distpath dist
xcopy /i /y sm.ico                      dist\
xcopy /i /y sm.png                      dist\
xcopy /i /y config.json                 dist\
xcopy /s /e /i  config                  dist\
xcopy /s /e /i  res                     dist\
