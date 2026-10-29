# Building the OpenGonsult Debian Package

This document describes how to build a Debian (.deb) package from the OpenGonsult git repository.

## Prerequisites

- Debian/Ubuntu-based system
- `dpkg-dev` package installed (provides `dpkg-deb`, `debuild`)
- Basic build tools: `build-essential`
- Python 3.8+ development files

## Repository Structure

The OpenGonsult repository at `/home/harlemi/.openclaw/workspace/OpenGonsult` contains:

```
/OpenGonsult/
├── gui/              # Python source packages
├── debian-build/     # Pre-configured Debian packaging
│   ├── DEBIAN/       # Control files and scripts
│   │   ├── control   # Package metadata
│   │   └── postinst  # Post-install script
│   └── usr/          # Installed files
│       ├── bin/      # Executable scripts
│       └── share/    # Data files
└── packaging/        # Additional packaging scripts/patches
```

## Building the Package

### Method 1: Using `dpkg-deb` (simplest)

```bash
# 1. Navigate to the repository
cd /home/harlemi/.openclaw/workspace/OpenGonsult

# 2. Build the .deb package
dpkg-deb --build debian-build opengonsult_0.88-1jammy_all.deb
```

This creates `opengonsult_0.88-1jammy_all.deb` in the current directory.

### Method 2: Using `debuild` (more complete)

```bash
cd debian-build
debuild -us -uc
# or
dbuild
```

`-us -uc` skips GPG signing of the source and changes files (useful for local builds).

### Method 3: Using `setuptools` directly (if preferred)

Since this is a Python package, you could also build a wheel first:

```bash
pip wheel . -w dist/
# Then create a Debian package from the wheel
```

However, Method 1 or 2 is recommended since the `debian-build/` directory is already fully configured.

## Package Details

| Field | Value |
|-------|-------|
| **Package Name** | `opengonsult` |
| **Version** | `0.88-1jammy` |
| **Architecture** | `all` (pure Python, no compiled extensions) |
| **Maintainer** | OpenGonsult Maintainers <OpenGonsult@users.noreply.github.com> |
| **Dependencies** | `python3 (>= 3.8), python3-gi, gir1.2-gtk-4.0, python3-gi-cairo, python3-cairo, python3-serial` |
| **Description** | Nissan CONSULT-I diagnostic suite for Linux (GTK4) |
| **Installed Size** | 256 bytes |

## Post-Installation

After installing the package:

```bash
sudo dpkg -i opengonsult_0.88-1jammy_all.deb
```

The `postinst` script will:
- Update the desktop database
- Refresh GTK icon caches

The application can then be launched from your application menu or by running `opengonsult` from the command line.

## Files in debian-build/

- `DEBIAN/control` - Package metadata (name, version, dependencies, description)
- `DEBIAN/postinst` - Post-installation script
- `usr/share/opengonsult/` - All Python package files
- `usr/bin/opengonsult` - Entry point script that launches the application

## Tips

- The package is architecture `all`, meaning it works on any system architecture
- Version `0.88-1jammy` indicates this is version 0.88, revision 1, tailored for Ubuntu Jammy (22.04)
- If you need to modify package dependencies, edit `debian-build/DEBIAN/control`
- To rebuild after source changes, re-run the build command