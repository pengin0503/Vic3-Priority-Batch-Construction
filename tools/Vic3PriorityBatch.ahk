#Requires AutoHotkey v2.0
#SingleInstance Force

; Shift+Alt+click -> 5 highest-priority constructions
; Ctrl+Alt+click  -> 10 highest-priority constructions
;
; The combined click is consumed here and replaced by 5/10 plain Alt+clicks at the
; cursor. Each one is the vanilla "Alt+click = 1 level at the front of the queue"
; action, so the result does not depend on how Victoria 3 treats Shift+Alt or
; Ctrl+Alt itself. Works with or without the Priority Batch mod and with UI mods.
; Only active while victoria3.exe is the foreground window.

; Delay between repeated clicks. Raise it if fewer entries than expected are added.
ClickDelayMs := 60

; Mask Alt releases with an unassigned key instead of Ctrl, so no extra Ctrl tap reaches the game.
A_MenuMaskKey := "vkE8"

; Explicit modifier symbols are required: a bare "LButton::" hotkey does not fire
; while Shift, Ctrl or Alt is held.
#HotIf WinActive("ahk_exe victoria3.exe")
+!LButton::PriorityBatch(5, "Shift")
^!LButton::PriorityBatch(10, "Ctrl")
#HotIf

PriorityBatch(count, extra) {
    ; Logically release Shift/Ctrl; {Blind} keeps the physically held Alt down.
    Send "{Blind}{L" extra " up}{R" extra " up}"
    Loop count {
        Click
        Sleep ClickDelayMs
    }
    ; Restore the modifier only if it is still physically held.
    if GetKeyState("L" extra, "P")
        Send "{Blind}{L" extra " down}"
    if GetKeyState("R" extra, "P")
        Send "{Blind}{R" extra " down}"
}
