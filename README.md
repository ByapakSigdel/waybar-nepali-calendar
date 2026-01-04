# Waybar Calendar Widget 📅

A modern, feature-rich calendar widget for Waybar, designed with a sleek "Next.js/Vercel" aesthetic. This widget provides seamless integration with Hyprland and supports both **Gregorian (AD)** and **Bikram Sambat (BS)** calendar systems.

![Calendar Preview](images/clipboard_image_1f84f76c2a02fb.png)

## ✨ Features

- **Dual Calendar Support**: Instantly toggle between AD (Gregorian) and BS (Bikram Sambat) calendars.
- **Event Management**: Add, view, and delete personal events directly from the widget.
- **Smart Positioning**: 
  - Automatically detects the monitor and cursor position.
  - Centers the popup relative to the Waybar clock.
  - Features a dynamic arrow indicator pointing to the source.
- **Dynamic Theming**: 
  - Automatically pulls colors from **Hyprland** active borders.
  - Supports **Pywal** color schemes.
  - Fallback to a beautiful **Catppuccin Mocha** theme.
- **Modern UI/UX**:
  - Transparent, blurred background (compositor dependent).
  - Smooth hover effects and transitions.
  - "Click-outside-to-close" functionality for a native popup feel.
- **Nepali Holidays**: Built-in support for major Nepali holidays and Tithis.

## 🖼️ Gallery

| AD View | BS View |
|---------|---------|
| ![AD View](images/clipboard_image_1f84f76c2a6bac.png) | ![BS View](images/clipboard_image_1f84f76c2afb6b.png) |

*Event Management:*
![Events](images/clipboard_image_1f84f76c2ba220.png)

## 🛠️ Prerequisites

Ensure you have the following installed on your system:

- **Python 3**
- **GTK 3**
- **GtkLayerShell** (libgtk-layer-shell)
- **Hyprland** (Recommended for automatic positioning and theming)
- **Waybar**

### Python Dependencies
The widget uses standard Python libraries (`gi`, `datetime`, `json`, `subprocess`), so no `pip install` is usually required if you have the system GTK bindings installed.

## 📦 Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/yourusername/waybar-calendar.git
   cd waybar-calendar
   ```

2. **Make the script executable**:
   ```bash
   chmod +x waybar_calendar.py
   ```

3. **Move to your Waybar config** (Optional but recommended):
   ```bash
   mkdir -p ~/.config/waybar/scripts
   cp -r * ~/.config/waybar/scripts/
   ```

## ⚙️ Configuration

### Waybar Config (`config.jsonc`)

Add the following to your Waybar module configuration to launch the calendar when clicking the clock:

```jsonc
"clock": {
    "format": "{:%H:%M}",
    "tooltip-format": "<big>{:%Y %B}</big>\n<tt><small>{calendar}</small></tt>",
    "on-click": "~/.config/waybar/scripts/waybar_calendar.py"
}
```

### Customizing Colors

The widget automatically attempts to fetch colors in this order:
1. **Hyprland Active Border**: Matches your window borders.
2. **Pywal**: Looks for `~/.cache/wal/colors.json`.
3. **Default**: Uses the Catppuccin Mocha palette.

To force specific colors, you can modify the `get_hyprland_colors()` function in `calendar_styles.py`.

## ⌨️ Usage

- **Open**: Click your Waybar clock.
- **Close**: Click anywhere outside the calendar widget or press `Esc`.
- **Switch Mode**: Click the **AD** / **BS** toggle buttons in the header.
- **Add Event**: Select a date, type in the "Add event..." box, and click `+` or press Enter.
- **Delete Event**: Click the `×` button next to an event in the list.
- **Navigation**: Use the `◀` and `▶` buttons to switch months.

## 📂 Project Structure

- `waybar_calendar.py`: Main application entry point and UI logic.
- `calendar_styles.py`: Handles CSS generation and theming.
- `bikram_sambat.py`: Core logic for Bikram Sambat date conversion and holidays.
- `bs_data/`: JSON data for BS calendar years.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 License

Distributed under the MIT License. See `LICENSE` for more information.
