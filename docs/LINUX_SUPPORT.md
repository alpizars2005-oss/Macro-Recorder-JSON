# Linux Support

## Supported environment

The project supports normal Linux graphical desktop sessions where `pynput` can access an X server or Xwayland.

The launcher checks for `DISPLAY` or `WAYLAND_DISPLAY` before starting. Headless SSH sessions are rejected with an actionable message.

## X11

X11 provides the most complete Linux behavior for global keyboard and mouse monitoring and playback.

## Wayland

Wayland intentionally restricts global input access. `pynput` commonly operates through Xwayland, which can limit input visibility to applications also running through Xwayland.

The application displays a warning when it detects a Wayland session. This is a platform limitation rather than a JSON or UI error.

## No root requirement

The project does not use the Linux uinput backend and does not request root access. Run it as the normal desktop user.

## Required system packages

### Ubuntu or Debian

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-tk
```

### Fedora

```bash
sudo dnf install -y python3 python3-tkinter
```

### Arch Linux

```bash
sudo pacman -S --needed python tk
```

Package names may differ on other distributions.

## Troubleshooting

Check the session type:

```bash
echo "$XDG_SESSION_TYPE"
echo "$DISPLAY"
echo "$WAYLAND_DISPLAY"
```

Verify the environment without launching the interface:

```bash
bash run_linux.sh --check-only
```

Recreate the disposable environment:

```bash
bash run_linux.sh --repair
```
