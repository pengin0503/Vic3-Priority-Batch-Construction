#Requires AutoHotkey v2.0
#SingleInstance Force

; Fallback only. Use this if the pure mod's combined modifiers are resolved as Alt
; by Jomini and therefore still add only one highest-priority construction.
; The $ prefix prevents the synthetic clicks below from recursively invoking the hotkey.

#HotIf WinActive("ahk_exe victoria3.exe") && GetKeyState("Alt", "P") && GetKeyState("Shift", "P") && !GetKeyState("Ctrl", "P")
$LButton::{
    Loop 5 {
        Click
        Sleep 20
    }
}

#HotIf WinActive("ahk_exe victoria3.exe") && GetKeyState("Alt", "P") && GetKeyState("Ctrl", "P") && !GetKeyState("Shift", "P")
$LButton::{
    Loop 10 {
        Click
        Sleep 20
    }
}
#HotIf
