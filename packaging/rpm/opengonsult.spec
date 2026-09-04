Name:           opengonsult
Version:        0.88
Release:        1%{?dist}
Summary:        Nissan CONSULT-I diagnostic suite for Linux (GTK4)

License:        GPL-3.0-or-later
URL:            https://github.com/wiczajac666/OpenGonsult
Source0:        %{name}-%{version}.tar.gz
BuildArch:      noarch

Requires:       python3 >= 3.8
Requires:       python3-gobject
Requires:       gtk4 >= 4.8
Requires:       python3-gobject
Requires:       python3-cairo
Requires:       python3-pyserial

%description
Open-source diagnostic tool for Nissan vehicles with the CONSULT-I
(14-pin) diagnostic interface, built as a native GTK4 application.

Features:
- Live dashboard with circular visual gauges (RPM, coolant temp,
  battery voltage, vehicle speed, throttle position, O2 sensor)
- Graphing page with multiple selectable sensor sources, zoom, pan
  and PNG export
- Diagnostics page with DTC reading, translations and clearing
- Settings page with serial device selection, baud rate and
  persistent dark mode
- Built-in simulation mode for hardware-free demonstration

%prep
%autosetup -n %{name}-%{version}

%build
# Pure Python, nothing to build.

%install
mkdir -p %{buildroot}%{_datadir}/%{name} \
         %{buildroot}%{_bindir} \
         %{buildroot}%{_datadir}/applications \
         %{buildroot}%{_datadir}/icons/hicolor/256x256/apps \
         %{buildroot}%{_mandir}/man1
cp -r gui ecu protocol serial graphs %{buildroot}%{_datadir}/%{name}/
install -p -m 0755 packaging/rpm/opengonsult-launcher %{buildroot}%{_bindir}/%{name}
install -p -m 0644 packaging/opengonsult.desktop %{buildroot}%{_datadir}/applications/%{name}.desktop
install -p -m 0644 icons/OpenGonsult.png %{buildroot}%{_datadir}/icons/hicolor/256x256/apps/%{name}.png
install -p -m 0644 packaging/rpm/opengonsult.1 %{buildroot}%{_mandir}/man1/%{name}.1

%files
%{_bindir}/%{name}
%{_datadir}/%{name}/
%{_datadir}/applications/%{name}.desktop
%{_datadir}/icons/hicolor/256x256/apps/%{name}.png
%{_mandir}/man1/%{name}.1.gz

%changelog
* Mon Aug 24 2026 OpenGonsult Maintainers <OpenGonsult@users.noreply.github.com> - 0.88-1
- Initial RPM packaging of OpenGonsult 0.88
- GTK4 GUI with visual gauges, graphing, diagnostics, settings and about pages
