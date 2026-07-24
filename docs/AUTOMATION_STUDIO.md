# Automation Studio

Automation Studio combines three visible, local automation tools in one workflow:

1. A saved Macro Recorder JSON macro.
2. Pixel-color triggers that can detect and click configured buttons such as **Restart** or **Replay**.
3. A Commander cycle that selects configured tower positions and presses one configured ability button.

It does not inject code into a game, read process memory, connect to a remote service, hide itself, or run as a background service. All interaction is ordinary visible keyboard, mouse, and screen sampling on the local computer.

## Launch

Windows PowerShell:

```powershell
.\run.bat --automation --language es
```

Or use the convenience launcher:

```powershell
.\run_automation.bat --language es
```

Linux desktop:

```bash
bash run_linux.sh --automation --language es
```

Or:

```bash
bash run_automation.sh --language es
```

## Recommended setup for a TDS workflow

### 1. Record the start-of-match actions

Open the normal recorder, perform only the actions that should happen after a map loads, stop with `F12`, and save the macro inside `macros/`.

Avoid recording passwords, chat, payment details, authentication codes, or other sensitive text.

### 2. Select the macro

Open Automation Studio and use **Browse** under **Start-of-match macro**. Enable **Run the selected macro when automation starts** only when the macro should also run during the first match.

### 3. Configure Restart and Replay

Open the end-of-match screen in the target application. For each button:

1. Enable the trigger that you want to use.
2. Choose **Capture under cursor**.
3. During the three-second delay, place the cursor over a safe, clickable part of the button.
4. Keep the cursor still until the Studio returns.

The Studio stores both the absolute screen position and the averaged RGB color around that point. The trigger must match several times in a row and is checked again immediately before the click. It stays latched until the button disappears, which prevents repeated clicks on the same screen.

Good starting values are:

- Color tolerance: `30`
- Required matches: `3`
- Cooldown: `3` seconds

### 4. Configure the Commander chain

Place the three Commander towers first. Then capture:

1. Commander 1
2. Commander 2
3. Commander 3
4. The Call to Arms ability button shown after selecting a Commander

Enable the chain and choose the interval. The Studio will select Commander 1, press the ability button, wait, continue with Commander 2, then Commander 3, and repeat.

The ability button must remain in the same screen position for all three Commanders. The towers must also remain visible and clickable.

### 5. Choose the load delay

Set **Wait after Restart/Replay** long enough for the map and interface to finish loading before the saved macro starts. A value between `8` and `15` seconds is a reasonable first test, but the correct value depends on the computer, connection, and game state.

### 6. Save the profile

Save it in `automations/`. Personal profile JSON files in that folder are ignored by Git because they can contain coordinates and local file paths.

### 7. Start safely

Keep the active-window rule set to `Roblox` unless you intentionally need a different window title. After choosing **Start automation**, switch to the intended window during the arming countdown.

Automation pauses its clicks when the configured window is not active. A saved macro is stopped if that window loses focus while the macro is running.

Press `F12` at any time to stop all Studio activity.

## Display and layout notes

Screen triggers and Commander positions use absolute coordinates. Re-capture them after changing any of the following:

- Screen resolution or display scaling
- Window size or position
- Full-screen versus windowed mode
- Monitor arrangement
- In-game interface scale

For the most reliable result, keep the target application in the same display mode and position used during setup.

## Linux note

The foreground-window protection uses `xdotool` on Linux. Install it through the distribution package manager when using the window-title guard. X11 or Xwayland is recommended; native Wayland can restrict global input and screen automation.

## Responsible use

Automation may be restricted by the rules of a game, service, workplace, school, or other platform. Review the applicable rules and use this feature only where you are authorized to do so. The project does not attempt to bypass anti-cheat, access controls, rate limits, or platform protections.
