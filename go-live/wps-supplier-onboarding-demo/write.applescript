on run argv
 set expectedTitle to item 1 of argv
 set cellAddress to item 2 of argv
 set cellValues to item 3 of argv
 set clicker to item 5 of argv
 set pauseSeconds to (item 4 of argv) as real
 tell application "System Events"
  tell process "wpsoffice"
   set frontmost to true
   if ((name of front window) does not contain expectedTitle) then error "Wrong WPS document"
   set {windowX, windowY} to position of front window
  end tell
 end tell
 set previousClipboard to the clipboard as record
 try
  do shell script quoted form of clicker & " " & (windowX + 77) & " " & (windowY + 205)
  delay 0.25
  set the clipboard to cellAddress
  tell application "System Events"
   keystroke "a" using command down
   keystroke "v" using command down
   key code 36
  end tell
  delay pauseSeconds
  tell application "System Events" to tell process "wpsoffice"
   if ((name of front window) does not contain expectedTitle) then error "WPS target lost before paste"
  end tell
  set the clipboard to cellValues
  tell application "System Events" to keystroke "v" using command down
  delay 0.45
  tell application "System Events" to keystroke "s" using command down
  delay 0.35
 on error errorText number errorNum
  set the clipboard to previousClipboard
  error errorText number errorNum
 end try
 set the clipboard to previousClipboard
end run
