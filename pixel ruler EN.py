import tkinter as tk
from tkinter import ttk, messagebox
import math
import pyautogui
from PIL import Image, ImageGrab
import threading
import time

class PersistentVisualRuler:
    def __init__(self, root):
        self.root = root
        self.root.title("Visual Drag Measurement Ruler")
        self.root.geometry("600x650")
        self.root.resizable(False, False)
        
        # Measurement state
        self.is_measuring = False
        self.start_point = None
        self.current_point = None
        self.dragging = False
        
        # Scale settings
        self.scale_factor = 100.0  # Default 100 pixels = 1 unit
        
        # Real-time display window
        self.overlay_window = None
        self.overlay_label = None
        
        # Fullscreen transparent window for event capture
        self.capture_window = None
        self.canvas = None
        
        # Line color and style
        self.line_color = "red"
        self.line_width = 2
        
        # Store all measurement lines
        self.measurement_lines = []  # Store (line_id, start_point, end_point, distance, real_distance)
        
        self.setup_ui()
        
    def setup_ui(self):
        # Main frame
        main_frame = ttk.Frame(self.root, padding="15")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        title_label = ttk.Label(main_frame, text="Visual Drag Measurement Ruler", 
                               font=("Arial", 14, "bold"))
        title_label.pack(pady=5)
        
        # Scale settings
        scale_frame = ttk.LabelFrame(main_frame, text="Scale Settings", padding="10")
        scale_frame.pack(fill=tk.X, pady=10)
        
        # Scale explanation
        scale_help = ttk.Label(scale_frame, text="Example: If 1cm=100 pixels on the drawing, enter 100", 
                              font=("Arial", 8), foreground="gray")
        scale_help.grid(row=0, column=0, columnspan=3, sticky=tk.W, pady=(0,5))
        
        ttk.Label(scale_frame, text="Scale (pixels/unit):").grid(row=1, column=0, padx=5)
        self.scale_entry = ttk.Entry(scale_frame, width=15)
        self.scale_entry.insert(0, "100")
        self.scale_entry.grid(row=1, column=1, padx=5)
        
        ttk.Button(scale_frame, text="Set", 
                  command=self.set_scale).grid(row=1, column=2, padx=10)
        
        # Line style settings
        style_frame = ttk.LabelFrame(main_frame, text="Line Style", padding="5")
        style_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(style_frame, text="Color:").grid(row=0, column=0, padx=5)
        self.color_var = tk.StringVar(value="red")
        color_combo = ttk.Combobox(style_frame, textvariable=self.color_var, 
                                  values=["red", "blue", "green", "yellow", "white", "black"], 
                                  width=8, state="readonly")
        color_combo.grid(row=0, column=1, padx=5)
        color_combo.bind('<<ComboboxSelected>>', self.change_line_color)
        
        ttk.Label(style_frame, text="Width:").grid(row=0, column=2, padx=5)
        self.width_var = tk.StringVar(value="2")
        width_combo = ttk.Combobox(style_frame, textvariable=self.width_var, 
                                  values=["1", "2", "3", "4", "5"], 
                                  width=5, state="readonly")
        width_combo.grid(row=0, column=3, padx=5)
        width_combo.bind('<<ComboboxSelected>>', self.change_line_width)
        
        # Button area
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(pady=15)
        
        self.start_btn = ttk.Button(btn_frame, text="Start Drag Measurement", 
                                   command=self.toggle_measurement,
                                   style="Accent.TButton")
        self.start_btn.pack(side=tk.LEFT, padx=10)
        
        ttk.Button(btn_frame, text="Clear Results", 
                  command=self.clear_results).pack(side=tk.LEFT, padx=10)
        
        #ttk.Button(btn_frame, text="Clear Lines", 
                 # command=self.clear_lines).pack(side=tk.LEFT, padx=10)
        
        ttk.Button(btn_frame, text="Exit", 
                  command=self.root.quit).pack(side=tk.LEFT, padx=10)
        
        # Status display
        self.status_label = ttk.Label(main_frame, text="Status: Ready", 
                                     foreground="green", font=("Arial", 10))
        self.status_label.pack(pady=5)
        
        # Results display
        result_frame = ttk.LabelFrame(main_frame, text="Measurement Results", padding="10")
        result_frame.pack(fill=tk.X, pady=10)
        
        self.result_text = tk.Text(result_frame, height=3, width=50, 
                                  font=("Arial", 9), wrap=tk.WORD)
        scrollbar = ttk.Scrollbar(result_frame, orient=tk.VERTICAL, command=self.result_text.yview)
        self.result_text.configure(yscrollcommand=scrollbar.set)
        self.result_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.result_text.insert(tk.END, "No measurement results yet\n")
        self.result_text.config(state=tk.DISABLED)
        
        # Instructions
        help_text = """Instructions:
1. Set the scale (e.g., if 1cm=100 pixels on the drawing, enter 100)
2. Click "Start Drag Measurement"
3. Press and hold left mouse button to drag and measure on screen
4. Measurement line will be shown during dragging, release left button to complete
5. All measurement lines will remain visible until ESC is pressed
6. Press ESC to exit measurement mode and clear all lines"""
        
        help_label = ttk.Label(main_frame, text=help_text, 
                              justify=tk.LEFT, font=("Arial", 9))
        help_label.pack(pady=5)
        
        # Bind ESC key
        self.root.bind('<Escape>', self.stop_measurement)
        
    def set_scale(self):
        try:
            self.scale_factor = float(self.scale_entry.get())
            if self.scale_factor <= 0:
                raise ValueError
            messagebox.showinfo("Success", f"Scale set to: {self.scale_factor} pixels/unit")
        except ValueError:
            messagebox.showerror("Error", "Please enter a valid positive number")
            
    def change_line_color(self, event=None):
        self.line_color = self.color_var.get()
        
    def change_line_width(self, event=None):
        self.line_width = int(self.width_var.get())
            
    def toggle_measurement(self):
        if not self.is_measuring:
            self.start_measurement()
        else:
            self.stop_measurement()
            
    def start_measurement(self):
        if self.scale_factor <= 0:
            messagebox.showerror("Error", "Please set a valid scale first")
            return
            
        self.is_measuring = True
        self.start_btn.config(text="Stop Measurement")
        self.status_label.config(text="Status: Measuring... Hold left button to drag and measure", foreground="red")
        
        # Create fullscreen transparent window to capture mouse events
        self.create_capture_window()
        
        # Create real-time display window
        self.create_overlay_window()
        
        # Minimize main window
        self.root.iconify()
        
    def create_capture_window(self):
        """Create fullscreen transparent window to capture mouse events"""
        self.capture_window = tk.Toplevel(self.root)
        self.capture_window.attributes('-fullscreen', True)
        self.capture_window.attributes('-alpha', 0.3)  # Almost transparent
        self.capture_window.attributes('-topmost', True)
        self.capture_window.configure(cursor="crosshair", bg='black')
        
        # Create canvas for drawing measurement lines
        self.canvas = tk.Canvas(self.capture_window, highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.canvas.configure(bg='black')
        
        # Bind events
        self.canvas.bind('<Button-1>', self.on_mouse_down)
        self.canvas.bind('<B1-Motion>', self.on_mouse_drag)
        self.canvas.bind('<ButtonRelease-1>', self.on_mouse_up)
        self.capture_window.bind('<Escape>', self.stop_measurement)
        
        # Initialize temporary line ID
        self.temp_line_id = None
        
    def create_overlay_window(self):
        """Create real-time display small window"""
        self.overlay_window = tk.Toplevel(self.root)
        self.overlay_window.overrideredirect(True)  # No border
        self.overlay_window.attributes('-topmost', True)  # Always on top
        self.overlay_window.attributes('-alpha', 0.85)  # Transparency
        self.overlay_window.configure(bg='lightyellow')
        
        # Create display label
        self.overlay_label = tk.Label(self.overlay_window, 
                                     text="Hold left button to drag and measure", 
                                     bg='lightyellow', 
                                     fg='black',
                                     font=("Arial", 10, "bold"),
                                     padx=10, pady=5,
                                     relief=tk.SOLID,
                                     borderwidth=1)
        self.overlay_label.pack()
        
    def on_mouse_down(self, event):
        """Mouse button down event"""
        if self.is_measuring:
            self.start_point = (event.x_root, event.y_root)
            self.dragging = True
            self.update_overlay("Start measuring...", event.x_root, event.y_root)
            
    def on_mouse_drag(self, event):
        """Mouse drag event"""
        if self.is_measuring and self.dragging and self.start_point:
            current_point = (event.x_root, event.y_root)
            
            # Clear previous temporary line
            if self.temp_line_id:
                self.canvas.delete(self.temp_line_id)
            
            # Draw new temporary line
            self.temp_line_id = self.canvas.create_line(
                self.start_point[0], self.start_point[1],
                current_point[0], current_point[1],
                fill=self.line_color, width=self.line_width
            )
            
            # Calculate distance
            distance = math.sqrt(
                (current_point[0] - self.start_point[0])**2 + 
                (current_point[1] - self.start_point[1])**2
            )
            real_distance = distance / self.scale_factor
            
            # Update real-time display
            display_text = f"Pixels: {distance:.1f}\nActual: {real_distance:.2f}"
            self.update_overlay(display_text, event.x_root, event.y_root)
            
    def on_mouse_up(self, event):
        """Mouse button release event"""
        if self.is_measuring and self.dragging and self.start_point:
            end_point = (event.x_root, event.y_root)
            
            # Calculate final distance
            distance = math.sqrt(
                (end_point[0] - self.start_point[0])**2 + 
                (end_point[1] - self.start_point[1])**2
            )
            real_distance = distance / self.scale_factor
            
            # Convert temporary line to permanent line
            if self.temp_line_id:
                # Delete temporary line
                self.canvas.delete(self.temp_line_id)
                
                # Create permanent line
                permanent_line_id = self.canvas.create_line(
                    self.start_point[0], self.start_point[1],
                    end_point[0], end_point[1],
                    fill=self.line_color, width=self.line_width
                )
                
                # Store line information
                self.measurement_lines.append({
                    'line_id': permanent_line_id,
                    'start_point': self.start_point,
                    'end_point': end_point,
                    'pixel_distance': distance,
                    'real_distance': real_distance
                })
                
                self.temp_line_id = None
            
            # Record result
            self.record_result(distance, real_distance, self.start_point, end_point)
            
            # Update display
            self.update_overlay(f"Actual: {real_distance:.2f}", event.x_root, event.y_root)
            
        self.dragging = False
        self.start_point = None
        
    def update_overlay(self, text, x, y):
        """Update real-time display window position and content"""
        if self.overlay_window and self.overlay_label:
            self.overlay_label.config(text=text)
            # Position window next to mouse position
            self.overlay_window.geometry(f"+{x}+{y+20}")
            
    def stop_measurement(self, event=None):
        self.is_measuring = False
        self.dragging = False
        self.start_btn.config(text="Start Drag Measurement")
        self.status_label.config(text="Status: Ready", foreground="green")
        
        # Clear all measurement lines
        self.clear_lines()
        
        # Close capture window
        if self.capture_window:
            self.capture_window.destroy()
            self.capture_window = None
            
        # Close real-time display window
        if self.overlay_window:
            self.overlay_window.destroy()
            self.overlay_window = None
            
        # Restore main window
        self.root.deiconify()
        self.root.lift()
        
    def clear_results(self):
        self.result_text.config(state=tk.NORMAL)
        self.result_text.delete(1.0, tk.END)
        self.result_text.insert(tk.END, "No measurement results yet\n")
        self.result_text.config(state=tk.DISABLED)
        
    def clear_lines(self):
        """Clear all measurement lines"""
        if self.canvas:
            # Clear temporary line
            if self.temp_line_id:
                self.canvas.delete(self.temp_line_id)
                self.temp_line_id = None
                
            # Clear all permanent lines
            for line_info in self.measurement_lines:
                self.canvas.delete(line_info['line_id'])
            
            # Clear line list
            self.measurement_lines = []
        
    def record_result(self, pixel_distance, real_distance, start_point, end_point):
        """Record measurement result to text box"""
        self.result_text.config(state=tk.NORMAL)
        
        # Add separator (if not the first record)
        if self.result_text.get(1.0, tk.END).strip() != "No measurement results yet":
            self.result_text.insert(tk.END, "-" * 50 + "\n")
        
        # Insert new result
        result_str = (f"Start: ({start_point[0]}, {start_point[1]})\n"
                     f"End: ({end_point[0]}, {end_point[1]})\n"
                     f"Pixel distance: {pixel_distance:.2f}\n"
                     f"Actual length: {real_distance:.2f}\n\n")
        
        self.result_text.insert(tk.END, result_str)
        self.result_text.see(tk.END)  # Scroll to end
        self.result_text.config(state=tk.DISABLED)

def main():
   
    root = tk.Tk()
    app = PersistentVisualRuler(root)
    root.mainloop()

if __name__ == "__main__":
    main()