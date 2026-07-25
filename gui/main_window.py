"""
OpenConsult - GTK4 Main Window Implementation
Original open-source diagnostic tool for Nissan vehicles (14-pin connector)

This module implements the main application window with dark mode support.
"""

import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, Gdk, Gio, GLib
import os


class MainWindow(Gtk.ApplicationWindow):
    """Main application window for OpenConsult"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # Set up the main layout
        self.setup_ui()
        
        # Connect signals
        self.connect("destroy", Gtk.main_quit)
        
        # Initialize state
        self.is_connected = False
        self.current_ecu = None
        
    def setup_ui(self):
        """Setup the user interface"""
        self.set_title("OpenConsult - Nissan Diagnostic Tool")
        self.set_default_size(1200, 800)
        self.set_icon_name("org.gnome.Terminal")
        
        # Main container with dark theme support
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.add(main_box)
        
        # Menu bar
        menu_bar = self.create_menu_bar()
        main_box.pack_start(menu_bar, False, False, 0)
        
        # Toolbar
        toolbar = self.create_toolbar()
        main_box.pack_start(toolbar, False, False, 0)
        
        # Status bar
        status_bar = Gtk.Statusbar()
        main_box.pack_end(status_bar, False, False, 0)
        self.status_bar = status_bar
        
        # Main content area with notebook for tabs
        notebook = Gtk.Notebook()
        main_box.pack_start(notebook, True, True, 0)
        
        # Create initial pages
        self.create_dashboard_page(notebook)
        self.create_graphs_page(notebook)
        self.create_diagnostics_page(notebook)
        self.create_settings_page(notebook)
        
    def create_menu_bar(self):
        """Create the application menu bar"""
        menubar = Gtk.MenuBar()
        
        # File menu
        file_menu = Gtk.MenuButton(label="File", use_underline=True)
        file_popup = Gtk.PopoverMenu()
        file_popup.set_halign(Gtk.Align.CENTER)
        
        new_session_item = Gtk.MenuItem.new_with_label("New Session")
        new_session_item.connect("activate", self.on_new_session)
        file_popup.append_menu_item(new_session_item)
        
        load_session_item = Gtk.MenuItem.new_with_label("Load Session")
        load_session_item.connect("activate", self.on_load_session)
        file_popup.append_menu_item(load_session_item)
        
        save_session_item = Gtk.MenuItem.new_with_label("Save Session")
        save_session_item.connect("activate", self.on_save_session)
        file_popup.append_menu_item(save_session_item)
        
        exit_item = Gtk.MenuItem.new_with_label("Exit")
        exit_item.set_sensitive(False)  # Will be enabled when needed
        file_popup.append_menu_item(exit_item)
        
        file_menu.set_popover(file_popup)
        menubar.append(file_menu)
        
        # Connection menu
        connection_menu = Gtk.MenuButton(label="Connection", use_underline=True)
        connection_popup = Gtk.PopoverMenu()
        connection_popup.set_halign(Gtk.Align.CENTER)
        
        connect_item = Gtk.MenuItem.new_with_label("Connect")
        connect_item.connect("activate", self.on_connect)
        connection_popup.append_menu_item(connect_item)
        
        disconnect_item = Gtk.MenuItem.new_with_label("Disconnect")
        disconnect_item.set_sensitive(False)
        disconnect_item.connect("activate", self.on_disconnect)
        connection_popup.append_menu_item(disconnect_item)
        
        connection_menu.set_popover(connection_popup)
        menubar.append(connection_menu)
        
        # Tools menu
        tools_menu = Gtk.MenuButton(label="Tools", use_underline=True)
        tools_popup = Gtk.PopoverMenu()
        tools_popup.set_halign(Gtk.Align.CENTER)
        
        ecu_info_item = Gtk.MenuItem.new_with_label("ECU Information")
        ecu_info_item.connect("activate", self.on_ecu_info)
        tools_popup.append_menu_item(ecu_info_item)
        
        dtc_reader_item = Gtk.MenuItem.new_with_label("Read DTCs")
        dtc_reader_item.connect("activate", self.on_read_dtcs)
        tools_popup.append_menu_item(dtc_reader_item)
        
        clear_dtc_item = Gtk.MenuItem.new_with_label("Clear DTCs")
        clear_dtc_item.set_sensitive(False)  # Enable when connected
        clear_dtc_item.connect("activate", self.on_clear_dtcs)
        tools_popup.append_menu_item(clear_dtc_item)
        
        tools_menu.set_popover(tools_popup)
        menubar.append(tools_menu)
        
        # Help menu
        help_menu = Gtk.MenuButton(label="Help", use_underline=True)
        help_popup = Gtk.PopoverMenu()
        help_popup.set_halign(Gtk.Align.CENTER)
        
        about_item = Gtk.MenuItem.new_with_label("About OpenConsult")
        about_item.connect("activate", self.on_about)
        help_popup.append_menu_item(about_item)
        
        help_menu.set_popover(help_popup)
        menubar.append(help_menu)
        
        return menubar
    
    def create_toolbar(self):
        """Create the toolbar with quick access buttons"""
        toolbar = Gtk.Toolbar()
        
        # Connection button
        connect_button = Gtk.ToolButton.new_from_icon_name(
            "network-transmit", Gtk.IconSize.LARGE_TOOLBAR)
        connect_button.set_label("Connect")
        connect_button.set_tooltip_text("Connect to ECU")
        connect_button.connect("clicked", self.on_connect)
        toolbar.insert(connect_button, -1)
        
        # Separator
        separator = Gtk.SeparatorToolItem.new()
        separator.set_expand(True)
        toolbar.insert(separator, -1)
        
        # Dashboard button
        dashboard_button = Gtk.ToolButton.new_from_icon_name(
            "view-list", Gtk.IconSize.LARGE_TOOLBAR)
        dashboard_button.set_label("Dashboard")
        dashboard_button.set_tooltip_text("Live sensor display")
        toolbar.insert(dashboard_button, -1)
        
        # Graphs button
        graphs_button = Gtk.ToolButton.new_from_icon_name(
            "chart-line", Gtk.IconSize.LARGE_TOOLBAR)
        graphs_button.set_label("Graphs")
        graphs_button.set_tooltip_text("Data visualization")
        toolbar.insert(graphs_button, -1)
        
        # DTC button
        dtc_button = Gtk.ToolButton.new_from_icon_name(
            "dialog-warning", Gtk.IconSize.LARGE_TOOLBAR)
        dtc_button.set_label("DTCs")
        dtc_button.set_tooltip_text("Diagnostic trouble codes")
        toolbar.insert(dtc_button, -1)
        
        return toolbar
    
    def create_dashboard_page(self, notebook):
        """Create the live dashboard page with RPM/temperature/voltage gauges (v0.69+)"""
        from ecu.sensor_reader import DashboardDataProcessor, SensorType
        
        # Initialize data processor for real-time gauge updates
        self.data_processor = DashboardDataProcessor()
        
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        page.set_margin_top(10)
        page.set_margin_bottom(10)
        page.set_margin_start(10)
        page.set_margin_end(10)
        
        # Title
        title_label = Gtk.Label(label="Live Dashboard", xalign=0.5)
        title_label.add_css_class("title-2")
        page.pack_start(title_label, False, False, 0)
        
        # Gauge container with circular progress indicators (RPM/temp/voltage)
        gauge_container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=15)
        gauge_container.set_margin_top(20)
        page.pack_start(gauge_container, True, True, 0)
        
        # Engine RPM Gauge
        rpm_box = self.create_gauge_section("Engine RPM", "RPM")
        self.rpm_progress_bar = Gtk.ProgressBar()
        rpm_box.pack_start(self.rpm_progress_bar, False, False, 5)
        gauge_container.pack_start(rpm_box, True, True, 0)
        
        # Coolant Temperature Gauge
        temp_box = self.create_gauge_section("Coolant Temp", "°C")
        self.temp_progress_bar = Gtk.ProgressBar()
        temp_box.pack_start(self.temp_progress_bar, False, False, 5)
        gauge_container.pack_start(temp_box, True, True, 0)
        
        # Battery Voltage Gauge
        voltage_box = self.create_gauge_section("Battery Voltage", "V")
        self.voltage_progress_bar = Gtk.ProgressBar()
        voltage_box.pack_start(self.voltage_progress_bar, False, False, 5)
        gauge_container.pack_start(voltage_box, True, True, 0)
        
        # Update loop for dashboard (called every second to refresh gauges)
        GLib.timeout_add_seconds(1, self.update_dashboard_gauges)
        
        notebook.append_page(page, Gtk.Label.new("Dashboard"))
    
    def create_graphs_page(self, notebook):
        """Create the graphs visualization page"""
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        page.set_margin_top(10)
        page.set_margin_bottom(10)
        page.set_margin_start(10)
        page.set_margin_end(10)
        
        # Title
        title_label = Gtk.Label(label="Data Graphs", xalign=0.5)
        title_label.add_css_class("title-2")
        page.pack_start(title_label, False, False, 0)
        
        # Graph area (placeholder for matplotlib integration)
        graph_area = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        graph_area.set_hexpand(True)
        graph_area.set_vexpand(True)
        graph_area.add_css_class("graph-container")
        
        placeholder_label = Gtk.Label(label="Graph visualization will appear here\nwhen connected to ECU", 
                                     xalign=0.5, yalign=0.5)
        graph_area.pack_start(placeholder_label, True, True, 0)
        
        page.pack_start(graph_area, True, True, 0)
        
        notebook.append_page(page, Gtk.Label.new("Graphs"))
    
    def create_diagnostics_page(self, notebook):
        """Create the diagnostics page"""
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        page.set_margin_top(10)
        page.set_margin_bottom(10)
        page.set_margin_start(10)
        page.set_margin_end(10)
        
        # Title
        title_label = Gtk.Label(label="Diagnostics", xalign=0.5)
        title_label.add_css_class("title-2")
        page.pack_start(title_label, False, False, 0)
        
        # DTC display area
        dtc_area = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        dtc_area.set_hexpand(True)
        dtc_area.set_vexpand(True)
        
        dtc_list_view = Gtk.ListBox()
        dtc_list_view.add_css_class("boxed-list")
        
        # Placeholder for DTC list
        no_dtcs_label = Gtk.Label(label="No diagnostic trouble codes found", 
                                 xalign=0.5, yalign=0.5)
        no_dtcs_label.set_ellipsize(3)  # PANGO_ELLIPSIZE_MIDDLE
        
        scroll_view = Gtk.ScrolledWindow()
        scroll_view.set_min_content_height(200)
        scroll_view.add(dtc_list_view)
        
        dtc_area.pack_start(scroll_view, True, True, 0)
        page.pack_start(dtc_area, True, True, 0)
        
        notebook.append_page(page, Gtk.Label.new("Diagnostics"))
    
    def create_settings_page(self, notebook):
        """Create the settings page"""
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        page.set_margin_top(10)
        page.set_margin_bottom(10)
        page.set_margin_start(10)
        page.set_margin_end(10)
        
        # Title
        title_label = Gtk.Label(label="Settings", xalign=0.5)
        title_label.add_css_class("title-2")
        page.pack_start(title_label, False, False, 0)
        
        # Settings form
        settings_grid = Gtk.Grid()
        settings_grid.set_column_spacing(10)
        settings_grid.set_row_spacing(10)
        settings_grid.set_margin_top(10)
        page.pack_start(settings_grid, True, True, 0)
        
        # Serial port selection
        label_serial = Gtk.Label(label="Serial Port:")
        settings_grid.attach(label_serial, 0, 0, 1, 1)
        
        self.serial_port_combo = Gtk.ComboBoxText.new()
        self.serial_port_combo.set_hexpand(True)
        self.serial_port_combo.append_text("/dev/ttyUSB0")
        self.serial_port_combo.append_text("/dev/ttyUSB1") 
        self.serial_port_combo.append_text("Bluetooth COM Port")
        settings_grid.attach(self.serial_port_combo, 1, 0, 2, 1)
        
        # Baud rate selection
        label_baud = Gtk.Label(label="Baud Rate:")
        settings_grid.attach(label_baud, 0, 1, 1, 1)
        
        self.baud_rate_combo = Gtk.ComboBoxText.new()
        self.baud_rate_combo.set_hexpand(True)
        for rate in [9600, 19200, 38400, 57600, 115200]:
            self.baud_rate_combo.append_text(str(rate))
        self.baud_rate_combo.set_active(4)  # Default to 115200
        settings_grid.attach(self.baud_rate_combo, 1, 1, 2, 1)
        
        # Dark mode toggle
        label_dark = Gtk.Label(label="Dark Mode:")
        settings_grid.attach(label_dark, 0, 2, 1, 1)
        
        self.dark_mode_switch = Gtk.Switch()
        self.dark_mode_switch.set_active(True)
        self.dark_mode_switch.connect("state-set", self.on_dark_mode_toggled)
        settings_grid.attach(self.dark_mode_switch, 1, 2, 1, 1)
        
        notebook.append_page(page, Gtk.Label.new("Settings"))
    
    def on_new_session(self, widget):
        """Handle new session creation"""
        self.status_bar.push(0, "New session created")
        
    def on_load_session(self, widget):
        """Handle loading a session"""
        dialog = Gtk.FileChooserDialog(
            title="Load Session",
            parent=self,
            action=Gtk.FileChooserAction.OPEN)
        dialog.add_buttons("Cancel", Gtk.ResponseType.CANCEL,
                          "Open", Gtk.ResponseType.OK)
        
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            filename = dialog.get_filename()
            self.status_bar.push(0, f"Loaded session: {filename}")
        dialog.destroy()
        
    def on_save_session(self, widget):
        """Handle saving a session"""
        dialog = Gtk.FileChooserDialog(
            title="Save Session",
            parent=self,
            action=Gtk.FileChooserAction.SAVE)
        dialog.add_buttons("Cancel", Gtk.ResponseType.CANCEL,
                          "Save", Gtk.ResponseType.OK)
        
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            filename = dialog.get_filename()
            self.status_bar.push(0, f"Saved session to: {filename}")
        dialog.destroy()
        
    def on_connect(self, widget):
        """Handle connection request"""
        port = self.serial_port_combo.get_active_text()
        baud_rate = int(self.baud_rate_combo.get_active_text())
        
        # In a real implementation, this would connect to the ECU
        self.status_bar.push(0, f"Connecting to {port} at {baud_rate} baud...")
        self.is_connected = True
        
    def on_disconnect(self, widget):
        """Handle disconnection"""
        self.status_bar.push(0, "Disconnected from ECU")
        self.is_connected = False
        
    def on_ecu_info(self, widget):
        """Display ECU information"""
        dialog = Gtk.MessageDialog(
            transient_for=self,
            message_type=Gtk.MessageType.INFO,
            buttons=Gtk.ButtonsType.OK,
            text="ECU Information")
        dialog.format_secondary_text("ECU identification and details will be displayed here when connected.")
        dialog.run()
        dialog.destroy()
        
    def on_read_dtcs(self, widget):
        """Read diagnostic trouble codes"""
        if not self.is_connected:
            dialog = Gtk.MessageDialog(
                transient_for=self,
                message_type=Gtk.MessageType.WARNING,
                buttons=Gtk.ButtonsType.OK,
                text="Connection Required")
            dialog.format_secondary_text("Please connect to an ECU first.")
            dialog.run()
            dialog.destroy()
        else:
            self.status_bar.push(0, "Reading DTCs...")
            
    def on_clear_dtcs(self, widget):
        """Clear diagnostic trouble codes"""
        if not self.is_connected:
            return
            
        dialog = Gtk.MessageDialog(
            transient_for=self,
            message_type=Gtk.MessageType.QUESTION,
            buttons=Gtk.ButtonsType.YES_NO,
            text="Clear DTCs")
        dialog.format_secondary_text("Are you sure you want to clear all diagnostic trouble codes?")
        
        response = dialog.run()
        if response == Gtk.ResponseType.YES:
            self.status_bar.push(0, "DTCs cleared successfully")
        dialog.destroy()
        
    def on_about(self, widget):
        """Display about dialog"""
        dialog = Gtk.AboutDialog(transient_for=self)
        dialog.set_program_name("OpenConsult")
        dialog.set_version("1.0.0")
        dialog.set_comments("Nissan CONSULT-I Diagnostic Tool for Linux")
        dialog.set_license_type(Gtk.License.GPL_3_0)
        dialog.run()
        dialog.destroy()
        
    def on_dark_mode_toggled(self, switch, state):
        """Handle dark mode toggle"""
        css_provider = Gtk.CssProvider()
        
        if state:
            css_content = b"""
                window { background-color: #2d2d2d; color: white; }
                .title-2 { font-size: 1.5em; font-weight: bold; }
                .graph-container { background-color: #1e1e1e; border-radius: 8px; padding: 10px; }
            """
        else:
            css_content = b"""
                window { background-color: white; color: black; }
                .title-2 { font-size: 1.5em; font-weight: bold; }
                .graph-container { background-color: #f0f0f0; border-radius: 8px; padding: 10px; }
            """
            
        css_provider.load_from_data(css_content)
        
        screen = Gdk.Screen.get_default()
        Gtk.StyleContext.add_provider_for_screen(
            screen, css_provider, 
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
    
    def create_gauge_section(self, label_text: str, unit_label: str) -> Gtk.Box:
        """Create a gauge display section with progress bar (used for RPM/temp/voltage gauges v0.69+)"""
        container = Gtk.Grid()
        container.set_column_spacing(8)
        
        # Label row
        label_widget = Gtk.Label(label=label_text, xalign=0)
        unit_label_widget = Gtk.Label(label=f" {unit_label}", xalign=1)
        container.attach(label_widget, 0, 0, 2, 1)  
        container.attach(unit_label_widget, 0, 1, 2, 1)  # Below the main label
        return container
    
    def update_dashboard_gauges(self):
        """Refresh gauge displays every second (called via GLib timeout for real-time updates v0.69+)"""
        if hasattr(self, 'data_processor') and self.data_processor:
            # Engine RPM - 0-8000 range typical
            rpm_value = self.data_processor.get_current_value(SensorType.ENGINE_RPM)
            if rpm_value is not None:
                max_rpm = 8000.0
                progress = min(1.0, (rpm_value / max_rpm))
                GLib.idle_add(self.rpm_progress_bar.set_fraction, float(progress))
                
            # Coolant Temp - -40 to +150°C range typical
            temp_value = self.data_processor.get_current_value(SensorType.COOLANT_TEMP)
            if temp_value is not None:
                min_temp, max_temp = -40.0, 150.0
                progress = (temp_value - min_temp) / (max_temp - min_temp)
                GLib.idle_add(self.temp_progress_bar.set_fraction, float(max(0, min(1, progress))))
            
            # Battery Voltage - ~9 to 16V range typical
            voltage_value = self.data_processor.get_current_value(SensorType.BATTERY_VOLTAGE)  
            if voltage_value is not None:
                min_volt, max_volt = 8.0, 16.0
                progress = (voltage_value - min_volt) / (max_volt - min_volt)
                GLib.idle_add(self.voltage_progress_bar.set_fraction, float(max(0, min(1, progress))))
        
        # Continue updates every second
        return True


class Application(Gtk.Application):
    """Main application class"""
    
    def __init__(self):
        super().__init__(application_id="org.openconsult.app",
                        flags=Gio.ApplicationFlags.FLAGS_NONE)
        
    def do_activate(self):
        """Handle application activation"""
        if not hasattr(self, 'window'):
            self.window = MainWindow(application=self)
            
        self.window.present()


def main():
    """Main entry point for OpenConsult"""
    app = Application()
    return app.run(None)


if __name__ == "__main__":
    main()