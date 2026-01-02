#!/usr/bin/env python3
"""
Waybar Calendar Widget with Bikram Sambat Support
A GTK Layer Shell based calendar popup for Waybar supporting both AD and BS calendars
"""

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('GtkLayerShell', '0.1')
from gi.repository import Gtk, Gdk, GLib, GtkLayerShell
import calendar
import datetime
import json
import os
import sys
import subprocess
import time
from pathlib import Path

# Add current directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

# Import modules
from calendar_styles import get_hyprland_colors, get_styled_css
from bikram_sambat import (
    get_bs_month_data, 
    ad_to_bs_date, 
    format_bs_date, 
    get_events_for_ad_date,
    NEPALI_MONTHS_EN
)

def get_cursor_pos_hyprctl():
    """Get cursor position using hyprctl (reliable on Wayland)"""
    try:
        result = subprocess.run(['hyprctl', 'cursorpos'], capture_output=True, text=True)
        if result.returncode == 0:
            # Output format: "123, 456"
            parts = result.stdout.strip().split(',')
            if len(parts) == 2:
                return int(parts[0]), int(parts[1])
    except Exception as e:
        with open("/tmp/waybar_calendar_error.log", "a") as f:
            f.write(f"Hyprctl cursor error: {e}\n")
    return None

def get_monitor_geometry_hyprctl(cx, cy):
    """Find which monitor contains the cursor using hyprctl"""
    try:
        result = subprocess.run(['hyprctl', 'monitors', '-j'], capture_output=True, text=True)
        if result.returncode == 0:
            monitors = json.loads(result.stdout)
            # First check for containment
            for m in monitors:
                mx, my = m['x'], m['y']
                mw, mh = m['width'], m['height']
                # Simple point in rect check
                if mx <= cx < mx + mw and my <= cy < my + mh:
                    return m
            
            # Fallback to focused
            for m in monitors:
                if m['focused']:
                    return m
            
            # Fallback to first
            if monitors:
                return monitors[0]
    except Exception as e:
        with open("/tmp/waybar_calendar_error.log", "a") as f:
            f.write(f"Hyprctl monitor error: {e}\n")
    return None

def get_waybar_position():
    """Get Waybar position from Hyprland"""
    try:
        result = subprocess.run(
            ['hyprctl', 'clients', '-j'], 
            capture_output=True, 
            text=True, 
            timeout=1
        )
        if result.returncode == 0:
            clients = json.loads(result.stdout)
            for client in clients:
                class_name = client.get('class', '').lower()
                if 'waybar' in class_name or 'bar' in class_name:
                    return {
                        'x': client['at'][0],
                        'y': client['at'][1],
                        'width': client['size'][0],
                        'height': client['size'][1]
                    }
    except:
        pass
    return None


class CalendarWidget(Gtk.Window):
    """Main calendar widget class with BS/AD support"""
    
    def __init__(self, mode='month'):
        super().__init__(title="Calendar")
        
        self.start_time = time.time()
        
        # State management
        self.mode = mode
        self.current_date = datetime.date.today()
        self.selected_date = datetime.date.today()
        self.events = self.load_events()
        self.colors = get_hyprland_colors()
        self.calendar_type = 'ad'  # 'ad' or 'bs'
        self.bs_current_date = ad_to_bs_date(self.current_date)
        
        # Initialize GTK Layer Shell
        self.init_layer_shell()
        
        # Setup window
        self.set_decorated(False)
        # self.set_default_size(750, 450) # Removed to allow fullscreen
        
        # Enable transparency
        screen = self.get_screen()
        visual = screen.get_rgba_visual()
        if visual and screen.is_composited():
            self.set_visual(visual)
        
        # Enable keyboard interactivity for focus-out dismissal
        GtkLayerShell.set_keyboard_mode(self, GtkLayerShell.KeyboardMode.ON_DEMAND)
        self.connect("focus-out-event", self.on_focus_out)
        
        # Apply styling
        self.apply_theme()
        
        # Fullscreen transparent overlay
        self.set_app_paintable(True)
        
        # Root Fixed Container
        self.fixed = Gtk.Fixed()
        self.add(self.fixed)
        
        # Clickable background to close
        self.bg_eventbox = Gtk.EventBox()
        self.bg_eventbox.set_visible_window(False) # Transparent
        self.bg_eventbox.connect("button-press-event", lambda w, e: Gtk.main_quit())
        self.fixed.put(self.bg_eventbox, 0, 0)
        
        # Main Vertical Box (Arrow + Content)
        self.vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        # We don't add vbox directly to window anymore, we put it in fixed
        self.fixed.put(self.vbox, 0, 0)
        
        # Arrow Container (Fixed for positioning arrow)
        self.arrow_container = Gtk.Fixed()
        self.arrow_container.set_size_request(-1, 10) # Height for arrow
        self.vbox.pack_start(self.arrow_container, False, False, 0)
        
        # Arrow Indicator
        self.arrow = Gtk.Box()
        self.arrow.set_size_request(0, 0) # Size handled by CSS
        self.arrow.get_style_context().add_class("arrow-up")
        self.arrow_container.put(self.arrow, 0, 0)
        
        # Create main container (Horizontal Split)
        self.main_container = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        self.main_container.get_style_context().add_class("main-container")
        self.main_container.get_style_context().add_class("popup-window") # New class for styling
        
        # Prevent clicks on container from closing window
        self.main_container.connect("button-press-event", lambda w, e: True)
        
        # Add to vbox
        self.vbox.pack_start(self.main_container, True, True, 0)
        
        # Left Pane (Events)
        self.events_pane = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.events_pane.get_style_context().add_class("events-pane")
        self.events_pane.set_size_request(250, -1) # Fixed width for events
        self.main_container.pack_start(self.events_pane, False, False, 0)
        
        # Right Pane (Calendar)
        self.calendar_pane = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.calendar_pane.get_style_context().add_class("calendar-pane")
        self.main_container.pack_start(self.calendar_pane, True, True, 0)
        
        # Build initial view
        self.refresh_ui()
        
        # Calculate initial position
        self.update_position()
        
        # Re-calculate position when mapped to ensure correct monitor
        self.connect("map", lambda w: self.update_position())
        
        # Show all widgets
        self.show_all()
        
        # Ensure focus
        GLib.timeout_add(100, self.present)
        GLib.timeout_add(200, lambda: self.get_window().focus(0))

    def on_focus_out(self, widget, event):
        # Ignore focus loss in the first 0.2s to prevent immediate closing
        if time.time() - self.start_time < 0.2:
            return False
            
        Gtk.main_quit()
        return False

    def init_layer_shell(self):
        GtkLayerShell.init_for_window(self)
        GtkLayerShell.set_layer(self, GtkLayerShell.Layer.TOP)
        
        # Anchor to all edges to make it fullscreen (for click-outside dismissal)
        GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.TOP, True)
        GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.BOTTOM, True)
        GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.LEFT, True)
        GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.RIGHT, True)
        
        # No margins needed for the window itself
        GtkLayerShell.set_margin(self, GtkLayerShell.Edge.TOP, 0)
        GtkLayerShell.set_margin(self, GtkLayerShell.Edge.LEFT, 0)
        GtkLayerShell.set_margin(self, GtkLayerShell.Edge.RIGHT, 0)
        GtkLayerShell.set_margin(self, GtkLayerShell.Edge.BOTTOM, 0)

    def update_position(self):
        try:
            # 1. Get Cursor Position (Hyprland specific)
            cursor_pos = get_cursor_pos_hyprctl()
            if not cursor_pos:
                # Fallback to GDK if hyprctl fails (unlikely on Hyprland)
                display = Gdk.Display.get_default()
                seat = display.get_default_seat()
                pointer = seat.get_pointer()
                screen, x, y = pointer.get_position()
            else:
                x, y = cursor_pos
            
            with open("/tmp/waybar_calendar_debug.log", "w") as f:
                f.write(f"Cursor: {x}, {y}\n")

            # 2. Get Monitor Info (Hyprland specific)
            hypr_monitor = get_monitor_geometry_hyprctl(x, y)
            
            window_width = 750
            
            if hypr_monitor:
                mx, my = hypr_monitor['x'], hypr_monitor['y']
                mw, mh = hypr_monitor['width'], hypr_monitor['height']
                
                with open("/tmp/waybar_calendar_debug.log", "a") as f:
                    f.write(f"HyprMonitor: {mx}, {my} {mw}x{mh} {hypr_monitor['name']}\n")
                
                # 3. Find matching GDK Monitor to set LayerShell
                display = Gdk.Display.get_default()
                gdk_monitor = None
                for i in range(display.get_n_monitors()):
                    m = display.get_monitor(i)
                    geo = m.get_geometry()
                    # Match by position and size
                    if geo.x == mx and geo.y == my:
                        gdk_monitor = m
                        break
                
                if gdk_monitor:
                    GtkLayerShell.set_monitor(self, gdk_monitor)
                
                # 4. Calculate Position
                # Calculate coordinates relative to the monitor
                rel_x = x - mx
                
                # Center popup on mouse X (relative)
                popup_x = int(rel_x - (window_width / 2))
                
                # Monitor bounds check
                if popup_x + window_width > mw:
                    popup_x = mw - window_width - 10
                if popup_x < 10:
                    popup_x = 10
                    
                with open("/tmp/waybar_calendar_debug.log", "a") as f:
                    f.write(f"Popup X: {popup_x}\n")
                    
                # Set Background Size
                self.bg_eventbox.set_size_request(mw, mh)
                
                # Move Main Container (Fixed positioning inside fullscreen window)
                # Note: Window is fullscreen, so (0,0) is top-left of monitor
                self.fixed.move(self.vbox, popup_x, 5)
                
                # Arrow X relative to the Window
                arrow_width = 20
                arrow_local_x = rel_x - popup_x - (arrow_width / 2)
                
                # Clamp arrow within window
                if arrow_local_x < 10:
                    arrow_local_x = 10
                if arrow_local_x > window_width - 30:
                    arrow_local_x = window_width - 30
                    
                # Move arrow
                self.arrow_container.move(self.arrow, int(arrow_local_x), 0)
                
            else:
                # Fallback
                self.fixed.move(self.vbox, 100, 5)
            
            # Force a redraw
            self.queue_draw()
            
        except Exception as e:
            with open("/tmp/waybar_calendar_error.log", "a") as f:
                f.write(f"Error in update_position: {e}\n")
                import traceback
                traceback.print_exc(file=f)

    def apply_theme(self):
        """Load CSS styling"""
        css_provider = Gtk.CssProvider()
        css_provider.load_from_data(get_styled_css())
        
        screen = Gdk.Screen.get_default()
        Gtk.StyleContext.add_provider_for_screen(
            screen, 
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )
    
    def refresh_ui(self):
        """Refresh both panes"""
        self.update_calendar_pane()
        self.update_events_pane()
    
    def update_calendar_pane(self):
        """Rebuild the calendar pane"""
        for child in self.calendar_pane.get_children():
            self.calendar_pane.remove(child)
            
        header = self.create_calendar_header()
        self.calendar_pane.pack_start(header, False, False, 0)
        
        if self.calendar_type == 'ad':
            grid = self.create_ad_calendar_grid()
        else:
            grid = self.create_bs_calendar_grid()
        
        self.calendar_pane.pack_start(grid, True, True, 0)
        self.calendar_pane.show_all()

    def update_events_pane(self):
        """Rebuild the events pane based on selected date"""
        for child in self.events_pane.get_children():
            self.events_pane.remove(child)
            
        header_label = Gtk.Label(label="EVENTS")
        header_label.get_style_context().add_class("header-label")
        header_label.set_halign(Gtk.Align.START)
        self.events_pane.pack_start(header_label, False, False, 0)
        
        date_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        
        ad_label = Gtk.Label()
        ad_label.set_markup(f'<span size="large" weight="bold">{self.selected_date.strftime("%A, %d %B")}</span>')
        ad_label.set_halign(Gtk.Align.START)
        date_box.pack_start(ad_label, False, False, 0)
        
        bs_date = ad_to_bs_date(self.selected_date)
        if bs_date:
            bs_text = format_bs_date(*bs_date)
            bs_label = Gtk.Label()
            bs_label.set_markup(f'<span color="{self.colors["accent"]}">{bs_text}</span>')
            bs_label.set_halign(Gtk.Align.START)
            date_box.pack_start(bs_label, False, False, 0)
            
        self.events_pane.pack_start(date_box, False, False, 10)
        
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        
        events_list = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        
        has_events = False
        
        bs_events = get_events_for_ad_date(self.selected_date)
        if bs_events:
            if bs_events.get('tithi'):
                tithi = Gtk.Label(label=f"Tithi: {bs_events['tithi']}")
                tithi.get_style_context().add_class("event-meta")
                tithi.set_halign(Gtk.Align.START)
                events_list.pack_start(tithi, False, False, 5)
            
            for event in bs_events.get('events', []):
                category = event.get('category', 'Holiday')
                row = self.create_event_row(event['title'], category, is_holiday=True)
                events_list.pack_start(row, False, False, 0)
                has_events = True
                
        date_str = self.selected_date.strftime("%Y-%m-%d")
        user_events = self.events.get(date_str, [])
        
        for i, event in enumerate(user_events):
            row = self.create_event_row(event, "Personal", index=i)
            events_list.pack_start(row, False, False, 0)
            has_events = True
            
        if not has_events:
            no_events = Gtk.Label(label="No events")
            no_events.get_style_context().add_class("event-meta")
            no_events.set_margin_top(20)
            events_list.pack_start(no_events, False, False, 0)
            
        scrolled.add(events_list)
        self.events_pane.pack_start(scrolled, True, True, 0)
        
        add_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        self.event_entry = Gtk.Entry()
        self.event_entry.set_placeholder_text("Add event...")
        self.event_entry.connect("activate", lambda e: self.add_current_event())
        
        add_btn = Gtk.Button(label="+")
        add_btn.get_style_context().add_class("add-event-btn")
        add_btn.connect("clicked", lambda b: self.add_current_event())
        
        add_box.pack_start(self.event_entry, True, True, 0)
        add_box.pack_start(add_btn, False, False, 0)
        
        self.events_pane.pack_start(add_box, False, False, 0)
        self.events_pane.show_all()

    def create_event_row(self, title, meta, is_holiday=False, index=None):
        row = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        row.get_style_context().add_class("event-item")
        
        title_label = Gtk.Label(label=title)
        title_label.get_style_context().add_class("event-title")
        title_label.set_halign(Gtk.Align.START)
        title_label.set_line_wrap(True)
        row.pack_start(title_label, False, False, 0)
        
        meta_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        meta_label = Gtk.Label(label=meta)
        meta_label.get_style_context().add_class("event-meta")
        meta_label.set_halign(Gtk.Align.START)
        meta_box.pack_start(meta_label, True, True, 0)
        
        if not is_holiday and index is not None:
            del_btn = Gtk.Button(label="×")
            del_btn.get_style_context().add_class("delete-btn")
            del_btn.set_relief(Gtk.ReliefStyle.NONE)
            del_btn.connect("clicked", lambda b: self.delete_event(index))
            meta_box.pack_start(del_btn, False, False, 0)
            
        row.pack_start(meta_box, False, False, 0)
        return row

    def add_current_event(self):
        text = self.event_entry.get_text().strip()
        if text:
            date_str = self.selected_date.strftime("%Y-%m-%d")
            if date_str not in self.events:
                self.events[date_str] = []
            self.events[date_str].append(text)
            self.save_events()
            self.update_events_pane()

    def delete_event(self, index):
        date_str = self.selected_date.strftime("%Y-%m-%d")
        if date_str in self.events:
            self.events[date_str].pop(index)
            if not self.events[date_str]:
                del self.events[date_str]
            self.save_events()
            self.update_events_pane()

    def create_calendar_header(self):
        header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        header_box.set_margin_bottom(15)
        
        month_label = Gtk.Label()
        month_label.get_style_context().add_class("month-label")
        month_label.set_xalign(0) # Left align text
        
        if self.calendar_type == 'ad':
            month_label.set_text(self.current_date.strftime("%B %Y").upper())
        else:
            if self.bs_current_date:
                y, m, _ = self.bs_current_date
                month_name = NEPALI_MONTHS_EN.get(m, '')
                month_label.set_text(f"{month_name} {y}".upper())
        
        header_box.pack_start(month_label, True, True, 0)
        
        controls = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        
        prev_btn = Gtk.Button(label="◀")
        prev_btn.get_style_context().add_class("nav-button")
        prev_btn.connect("clicked", lambda b: self.change_month(-1))
        
        next_btn = Gtk.Button(label="▶")
        next_btn.get_style_context().add_class("nav-button")
        next_btn.connect("clicked", lambda b: self.change_month(1))
        
        ad_btn = Gtk.RadioButton.new_with_label_from_widget(None, "AD")
        ad_btn.get_style_context().add_class("toggle-button")
        ad_btn.set_active(self.calendar_type == 'ad')
        ad_btn.connect("toggled", lambda b: self.toggle_calendar_type('ad') if b.get_active() else None)
        
        bs_btn = Gtk.RadioButton.new_with_label_from_widget(ad_btn, "BS")
        bs_btn.get_style_context().add_class("toggle-button")
        bs_btn.set_active(self.calendar_type == 'bs')
        bs_btn.connect("toggled", lambda b: self.toggle_calendar_type('bs') if b.get_active() else None)
        
        controls.pack_start(ad_btn, False, False, 0)
        controls.pack_start(bs_btn, False, False, 0)
        controls.pack_start(prev_btn, False, False, 0)
        controls.pack_start(next_btn, False, False, 0)
        
        header_box.pack_start(controls, False, False, 0)
        return header_box

    def create_ad_calendar_grid(self):
        grid = Gtk.Grid()
        grid.set_row_homogeneous(True)
        grid.set_column_homogeneous(True)
        grid.set_row_spacing(5)
        grid.set_column_spacing(5)
        
        weekdays = ['MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT', 'SUN']
        for i, day in enumerate(weekdays):
            label = Gtk.Label(label=day)
            label.get_style_context().add_class("weekday-label")
            grid.attach(label, i, 0, 1, 1)
        
        cal = calendar.monthcalendar(self.current_date.year, self.current_date.month)
        
        row = 1
        for week in cal:
            for col, day in enumerate(week):
                if day != 0:
                    date = datetime.date(self.current_date.year, self.current_date.month, day)
                    
                    # Check for BS events
                    bs_events = get_events_for_ad_date(date)
                    has_bs_event = False
                    if bs_events and bs_events.get('events'):
                        has_bs_event = True
                        
                    btn = self.create_day_button(str(day), date, has_event=has_bs_event)
                    grid.attach(btn, col, row, 1, 1)
            row += 1
        return grid

    def create_bs_calendar_grid(self):
        if not self.bs_current_date:
            return Gtk.Label(label="Loading...")
            
        year, month, _ = self.bs_current_date
        bs_data = get_bs_month_data(year, month)
        
        if not bs_data:
            return Gtk.Label(label="Unavailable")
            
        grid = Gtk.Grid()
        grid.set_row_homogeneous(True)
        grid.set_column_homogeneous(True)
        grid.set_row_spacing(5)
        grid.set_column_spacing(5)
        
        weekdays = ['SUN', 'MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT']
        for i, day in enumerate(weekdays):
            label = Gtk.Label(label=day)
            label.get_style_context().add_class("weekday-label")
            grid.attach(label, i, 0, 1, 1)
            
        matrix = [[None for _ in range(7)] for _ in range(6)]
        
        if bs_data['days']:
            first_day_weekday = bs_data['days'][0]['bs_day']
            current_row = 0
            current_col = first_day_weekday
            
            for day_info in bs_data['days']:
                matrix[current_row][current_col] = day_info
                current_col += 1
                if current_col > 6:
                    current_col = 0
                    current_row += 1
        
        for r, week in enumerate(matrix):
            for c, day_info in enumerate(week):
                if day_info:
                    ad_date = datetime.datetime.strptime(day_info['ad_date'], '%Y-%m-%d').date()
                    btn = self.create_day_button(str(day_info['bs_date']), ad_date, has_event=bool(day_info['events']))
                    grid.attach(btn, c, r+1, 1, 1)
                    
        return grid

    def create_day_button(self, label, date, has_event=False):
        btn = Gtk.Button(label=label)
        btn.get_style_context().add_class("calendar-day")
        btn.set_relief(Gtk.ReliefStyle.NONE)
        
        if date == datetime.date.today():
            btn.get_style_context().add_class("today")
            
        if date == self.selected_date:
            btn.get_style_context().add_class("selected")
            
        date_str = date.strftime("%Y-%m-%d")
        if has_event or date_str in self.events:
            btn.get_style_context().add_class("has-event")
            
        btn.connect("clicked", lambda b: self.on_day_clicked(date))
        return btn

    def on_day_clicked(self, date):
        self.selected_date = date
        self.refresh_ui()

    def toggle_calendar_type(self, cal_type):
        if self.calendar_type != cal_type:
            self.calendar_type = cal_type
            if cal_type == 'bs' and not self.bs_current_date:
                self.bs_current_date = ad_to_bs_date(self.current_date)
            self.update_calendar_pane()

    def change_month(self, delta):
        if self.calendar_type == 'ad':
            new_month = self.current_date.month + delta
            new_year = self.current_date.year
            if new_month > 12:
                new_month = 1
                new_year += 1
            elif new_month < 1:
                new_month = 12
                new_year -= 1
            self.current_date = self.current_date.replace(year=new_year, month=new_month)
        else:
            if self.bs_current_date:
                y, m, d = self.bs_current_date
                new_m = m + delta
                new_y = y
                if new_m > 12:
                    new_m = 1
                    new_y += 1
                elif new_m < 1:
                    new_m = 12
                    new_y -= 1
                self.bs_current_date = (new_y, new_m, 1)
                bs_data = get_bs_month_data(new_y, new_m)
                if bs_data and bs_data['days']:
                    self.current_date = datetime.datetime.strptime(bs_data['days'][0]['ad_date'], '%Y-%m-%d').date()
        
        self.update_calendar_pane()

    def on_key_press(self, widget, event):
        if event.keyval == Gdk.KEY_Escape:
            self.destroy()
            return True
        return False
    
    def load_events(self):
        events_file = Path.home() / '.config' / 'waybar' / 'calendar_events.json'
        if events_file.exists():
            try:
                with open(events_file, 'r') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def save_events(self):
        events_file = Path.home() / '.config' / 'waybar' / 'calendar_events.json'
        events_file.parent.mkdir(parents=True, exist_ok=True)
        with open(events_file, 'w') as f:
            json.dump(self.events, f, indent=2)

def check_if_running():
    pid_file = Path('/tmp/waybar_calendar.pid')
    if pid_file.exists():
        try:
            with open(pid_file, 'r') as f:
                old_pid = int(f.read().strip())
            os.kill(old_pid, 15)
            pid_file.unlink()
            return True
        except:
            pass
    with open(pid_file, 'w') as f:
        f.write(str(os.getpid()))
    return False

def main():
    if check_if_running():
        sys.exit(0)
    
    try:
        win = CalendarWidget()
        win.connect("destroy", Gtk.main_quit)
        win.show_all()
        Gtk.main()
    except Exception as e:
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
