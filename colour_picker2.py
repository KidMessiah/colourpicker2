# Import all the libraries we need
# pystray - for creating the system tray icon
# PIL (Python Imaging Library) - for image handling
# keyboard - for hotkey detection
# pyperclip - for copying to clipboard
# pyautogui - for getting mouse position
import pystray
from pystray import MenuItem as item
from PIL import Image
import keyboard
import pyperclip
import pyautogui
import sys
import time
import mss
import colorsys
import tkinter
import json
from tkinter import filedialog
import subprocess
import os

# Version info
__version__ = '2.0.0'
__author__ = 'Chris Nielebock'
__company__ = 'No Company'

# Function to get the color of a single pixel at coordinates (x,y)
def get_pixel_color(x, y):
    with mss.mss() as sct:
        bbox = {"top": y, "left": x, "width": 1, "height": 1}
        screenshot = sct.grab(bbox)
        return screenshot.pixel(0, 0)

# Convert the color to different formats (RGB, HSL, CMYK)
def get_pixel_color_formats(x, y):
    # Get the RGB values first
    rgb = get_pixel_color(x, y)
    r, g, b = [x / 255.0 for x in rgb]
    
    # Calculate HSL it's still off on anything with non-50 luminance idk wtf is going on
    max_val = max(r, g, b)
    min_val = min(r, g, b)
    delta = max_val - min_val
    
    # Calculate Luminance
    luminance = (max_val + min_val) / 2
    
    # Calculate Saturation
    saturation = 0
    if delta != 0:
        saturation = delta / (1 - abs(2 * luminance - 1))
    
    # Calculate Hue
    hue = 0
    if delta != 0:
        if max_val == r:
            hue = 60 * (((g - b) / delta) % 6)
        elif max_val == g:
            hue = 60 * (((b - r) / delta) + 2)
        elif max_val == b:
            hue = 60 * (((r - g) / delta) + 4)
        
        if hue < 0:
            hue += 360
    
    # Calculate CMYK
    k = 1 - max_val
    if k == 1:
        cmyk = (0, 0, 0, 100)
    else:
        c = (1 - r - k) / (1 - k)
        m = (1 - g - k) / (1 - k)
        yellow = (1 - b - k) / (1 - k)
        cmyk = (round(c * 100), round(m * 100), round(yellow * 100), round(k * 100))
    
    return {
        "rgb": (rgb[0], rgb[1], rgb[2]),
        "hsl": (round(hue), round(saturation * 100), round(luminance * 100)),
        "cmyk": cmyk
    }

# Convert RGB color to hexadecimal 
def get_pixel_color_hex(x, y):
    rgb = get_pixel_color(x, y)
    return '#{:02x}{:02x}{:02x}'.format(rgb[0], rgb[1], rgb[2])

# Variables to store the last picked color and history
last_picked_hex = None
last_picked_formats = None
color_history = []

tk_root = None
color_window = None
color_frames = []
MAX_COLORS = 15

grid_rows = 3
grid_cols = 5
control_panel = None

row_spinbox = None
col_spinbox = None

# This function updates the grid when user changes rows/columns
def update_grid_dimensions():
    global MAX_COLORS, grid_rows, grid_cols
    old_max = MAX_COLORS
    MAX_COLORS = grid_rows * grid_cols
    
    while len(color_frames) > MAX_COLORS:
        frame_to_remove = color_frames.pop()
        frame_to_remove.destroy()
        color_history.pop()
    
    reposition_frames()

# Rearrange color squares in the window based on grid settings
def reposition_frames():
    if not color_window or not color_window.winfo_exists():
        return
        
    color_window.update_idletasks()
    color_window.after(1, lambda: color_window.update())
    
    for i, frame in enumerate(color_frames):
        row = (i // grid_cols) + 1
        col = i % grid_cols
        frame.grid(row=row, column=col, padx=5, pady=5)

# Print debug messages (only when running from source, not from exe)
def log_message(message):
    if not getattr(sys, 'frozen', False):
        print(message)

# This runs when user presses ctrl+alt+c
def on_activate():
    log_message("Hotkey activated")
    # Wait a tiny bit to make sure the key press is done
    time.sleep(0.1)
    # Get the current mouse position and color under it
    x, y = pyautogui.position()
    color = get_pixel_color(x, y)
    hex_color = get_pixel_color_hex(x, y)
    pyperclip.copy(hex_color)
    log_message(f"Copied {hex_color} to clipboard")
    global last_picked_hex, last_picked_formats, color_history
    last_picked_hex = hex_color
    last_picked_formats = get_pixel_color_formats(x, y)
    
    if len(color_history) >= MAX_COLORS:
        color_history.pop(0)
        if color_frames:
            old_frame = color_frames.pop(0)
            old_frame.destroy()
    
    color_history.append((last_picked_hex, last_picked_formats))
    
    if color_window and color_window.winfo_exists():
        add_color_frame(last_picked_hex, last_picked_formats, len(color_frames))
        reposition_frames()
    
    log_message(f"RGB: {last_picked_formats['rgb']}, HSL: {last_picked_formats['hsl']}, CMYK: {last_picked_formats['cmyk']}")
    update_tray_icon(color)

# Copy different color formats to clipboard
def copy_to_clipboard(format):
    global last_picked_hex, last_picked_formats
    if last_picked_hex and last_picked_formats:
        if format == 'hex':
            color_str = last_picked_hex
        else:
            color_formats = last_picked_formats
            if format == 'rgb':
                color_str = f"rgb({color_formats['rgb'][0]}, {color_formats['rgb'][1]}, {color_formats['rgb'][2]})"
            elif format == 'hsl':
                hsl = color_formats['hsl']
                color_str = f"hsl({hsl[0]}, {hsl[1]}%, {hsl[2]}%)"
            elif format == 'cmyk':
                cmyk = color_formats['cmyk']
                color_str = f"cmyk({cmyk[0]}%, {cmyk[1]}%, {cmyk[2]}%, {cmyk[3]}%)"
        pyperclip.copy(color_str)
        log_message(f"Copied {color_str} to clipboard")

# Update the tray icon to show the last picked color
def update_tray_icon(color):
    icon_image = Image.new('RGB', (64, 64), color=color)
    icon.icon = icon_image

def on_exit():
    """Cleanup function to ensure proper program termination"""
    global icon, tk_root
    log_message("Exiting program...")
    keyboard.unhook_all()  # Remove all keyboard hooks
    if icon:
        icon.visible = False  # Hide the icon
        icon.stop()  # Stop the icon
    if color_window and color_window.winfo_exists():
        color_window.destroy()
    if tk_root:
        tk_root.destroy()  # Changed from quit() to destroy()
    os._exit(0)  # Force exit the program

def quit_program(icon, item):
    # Schedule the exit function to run in the main thread
    if tk_root:
        tk_root.after(0, on_exit)

# Calculate opposite color (for text visibility)
def get_inverse_color(rgb):
    return tuple(255 - c for c in rgb)

# Right-click menu functions for each color square
def copy_specific_color(hex_color, formats, format_type):
    if format_type == 'hex':
        color_str = hex_color
    elif format_type == 'rgb':
        color_str = f"rgb({formats['rgb'][0]}, {formats['rgb'][1]}, {formats['rgb'][2]})"
    elif format_type == 'hsl':
        hsl = formats['hsl']
        color_str = f"hsl({hsl[0]}, {hsl[1]}%, {hsl[2]}%)"
    elif format_type == 'cmyk':
        cmyk = formats['cmyk']
        color_str = f"cmyk({cmyk[0]}%, {cmyk[1]}%, {cmyk[2]}%, {cmyk[3]}%)"
    pyperclip.copy(color_str)
    log_message(f"Copied {color_str} to clipboard")

# Remove a color from history
def delete_color(hex_color):
    global color_history, color_frames
    
    for i, (h, _) in enumerate(color_history):
        if h == hex_color:
            color_history.pop(i)
            break
    
    refresh_color_display()

# Show right-click menu for color squares
def show_context_menu(event, hex_color, formats):
    context_menu = tkinter.Menu(tk_root, tearoff=0)
    context_menu.add_command(label="Copy HEX", command=lambda: copy_specific_color(hex_color, formats, 'hex'))
    context_menu.add_command(label="Copy RGB", command=lambda: copy_specific_color(hex_color, formats, 'rgb'))
    context_menu.add_command(label="Copy HSL", command=lambda: copy_specific_color(hex_color, formats, 'hsl'))
    context_menu.add_command(label="Copy CMYK", command=lambda: copy_specific_color(hex_color, formats, 'cmyk'))
    context_menu.add_separator()
    context_menu.add_command(label="Delete", command=lambda: delete_color(hex_color))
    context_menu.tk_popup(event.x_root, event.y_root)

# Save the current color palette to a file
def save_palette():
    if not color_history:
        return
        
    file_path = filedialog.asksaveasfilename(
        defaultextension=".json",
        filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
        title="Save Color Palette"
    )
    
    if not file_path:
        return
        
    palette_data = {
        "grid_rows": grid_rows,
        "grid_cols": grid_cols,
        "colors": []
    }
    
    for hex_color, formats in color_history:
        palette_data["colors"].append({
            "hex": hex_color,
            "formats": formats
        })
        
    try:
        with open(file_path, 'w') as f:
            json.dump(palette_data, f)
        log_message(f"Palette saved to {file_path}")
    except Exception as e:
        log_message(f"Error saving palette: {e}")

def update_spinboxes():
    global row_spinbox, col_spinbox
    if row_spinbox and col_spinbox:
        row_spinbox.delete(0, 'end')
        row_spinbox.insert(0, str(grid_rows))
        col_spinbox.delete(0, 'end')
        col_spinbox.insert(0, str(grid_cols))

# Load a previously saved color palette
def load_palette():
    file_path = filedialog.askopenfilename(
        filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
        title="Load Color Palette"
    )
    
    if not file_path:
        return
        
    try:
        with open(file_path, 'r') as f:
            palette_data = json.load(f)
            
        global color_history, grid_rows, grid_cols
        
        color_history.clear()
        
        if isinstance(palette_data, dict):
            grid_rows = palette_data.get("grid_rows", grid_rows)
            grid_cols = palette_data.get("grid_cols", grid_cols)
            colors_data = palette_data.get("colors", [])
        else:
            colors_data = palette_data
            
        global MAX_COLORS
        MAX_COLORS = grid_rows * grid_cols
            
        for color_data in colors_data:
            color_history.append((color_data["hex"], color_data["formats"]))
            
        if color_window and color_window.winfo_exists():
            for frame in color_frames:
                frame.destroy()
            color_frames.clear()
            
            update_spinboxes()
            
            refresh_color_display()
            
        log_message(f"Palette loaded from {file_path}")
    except Exception as e:
        log_message(f"Error loading palette: {e}")

def update_rows(spinbox):
    global grid_rows
    try:
        grid_rows = int(spinbox.get())
        update_grid_dimensions()
    except ValueError:
        pass
    
def update_cols(spinbox):
    global grid_cols
    try:
        grid_cols = int(spinbox.get())
        update_grid_dimensions()
    except ValueError:
        pass

# Create the window that shows color history
def show_color_window():
    global color_window, color_frames, control_panel, row_spinbox, col_spinbox
    
    if not color_window or not color_window.winfo_exists():
        color_window = tkinter.Toplevel(tk_root)
        color_window.title("Colour History")
        
        control_panel = tkinter.Frame(color_window)
        control_panel.grid(row=0, column=0, columnspan=5, pady=5)
        
        tkinter.Label(control_panel, text="Rows:").pack(side='left', padx=5)
        row_spinbox = tkinter.Spinbox(control_panel, from_=1, to=10, width=5,
                                    command=lambda: update_rows(row_spinbox))
        row_spinbox.delete(0, 'end')
        row_spinbox.insert(0, str(grid_rows))
        row_spinbox.pack(side='left', padx=5)
        
        tkinter.Label(control_panel, text="Columns:").pack(side='left', padx=5)
        col_spinbox = tkinter.Spinbox(control_panel, from_=1, to=10, width=5,
                                    command=lambda: update_cols(col_spinbox))
        col_spinbox.delete(0, 'end')
        col_spinbox.insert(0, str(grid_cols))
        col_spinbox.pack(side='left', padx=5)
        
        save_button = tkinter.Button(control_panel, text="Save Palette", command=save_palette)
        save_button.pack(side='left', padx=5)
        
        load_button = tkinter.Button(control_panel, text="Load Palette", command=load_palette)
        load_button.pack(side='left', padx=5)
        
        refresh_color_display()

# Create individual color squares in the window
def add_color_frame(hex_color, formats, index):
    # Create a frame (container) for this color
    frame = tkinter.Frame(color_window, width=225, height=150)
    color_frames.append(frame)
    
    # Calculate position in grid
    row = (index // grid_cols) + 1
    col = index % grid_cols
    frame.grid(row=row, column=col, padx=5, pady=5)
    
    inverse_rgb = get_inverse_color(formats['rgb'])
    inverse_hex = '#{:02x}{:02x}{:02x}'.format(*inverse_rgb)
    
    color_display = tkinter.Frame(frame, bg=hex_color)
    color_display.place(relwidth=1, relheight=1)
    
    info = f"Hex: {hex_color}\nRGB: {formats['rgb']}\nHSL: {formats['hsl']}\nCMYK: {formats['cmyk']}"
    label = tkinter.Label(color_display, text=info, bg=hex_color, fg=inverse_hex, 
                        justify='left', font=('TkDefaultFont', 10, 'bold'))
    label.place(relx=0.5, rely=0.5, anchor='center')
    
    frame.bind('<Button-3>', lambda e, h=hex_color, f=formats: show_context_menu(e, h, f))
    color_display.bind('<Button-3>', lambda e, h=hex_color, f=formats: show_context_menu(e, h, f))
    label.bind('<Button-3>', lambda e, h=hex_color, f=formats: show_context_menu(e, h, f))
    return frame

# Update the display when colors are added/removed
def refresh_color_display():
    global color_frames
    
    for frame in color_frames:
        frame.destroy()
    color_frames.clear()
    
    for i, (hex_color, formats) in enumerate(color_history[-MAX_COLORS:]):
        add_color_frame(hex_color, formats, i)
    
    reposition_frames()

# Create the system tray icon and menu
def setup_tray_icon():
    global icon
    icon_image = Image.new('RGB', (64, 64), color='white')
    icon = pystray.Icon("Colour Picker", icon_image, "Colour Picker", menu=pystray.Menu(
        item('Copy HEX', lambda: copy_to_clipboard('hex')),
        item('Copy RGB', lambda: copy_to_clipboard('rgb')),
        item('Copy HSL', lambda: copy_to_clipboard('hsl')),
        item('Copy CMYK', lambda: copy_to_clipboard('cmyk')),
        item('Show Colour', lambda: show_color_window()),
        item('Quit', quit_program)
    ))
    icon.run_detached()

# Main program starts here
if __name__ == "__main__":
    # Hide console window if running as exe
    if getattr(sys, 'frozen', False):
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = subprocess.SW_HIDE
    
    # Create the main window (but keep it hidden)
    tk_root = tkinter.Tk()
    tk_root.withdraw()
    
    # Add protocol handler for window close
    tk_root.protocol('WM_DELETE_WINDOW', on_exit)
    
    # Set up the hotkey and tray icon
    keyboard.add_hotkey('ctrl+alt+c', on_activate)
    setup_tray_icon()
    
    try:
        tk_root.mainloop()
    except KeyboardInterrupt:
        on_exit()
