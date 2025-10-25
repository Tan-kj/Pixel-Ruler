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
        self.root.title("可视化拖拽测量尺")
        self.root.geometry("450x650")
        self.root.resizable(False, False)
        
        # 测量状态
        self.is_measuring = False
        self.start_point = None
        self.current_point = None
        self.dragging = False
        
        # 比例尺设置
        self.scale_factor = 100.0  # 默认100像素=1单位
        
        # 实时显示窗口
        self.overlay_window = None
        self.overlay_label = None
        
        # 全屏透明窗口用于捕获事件
        self.capture_window = None
        self.canvas = None
        
        # 线条颜色和样式
        self.line_color = "red"
        self.line_width = 2
        
        # 存储所有测量线段
        self.measurement_lines = []  # 存储 (line_id, start_point, end_point, distance, real_distance)
        
        self.setup_ui()
        
    def setup_ui(self):
        # 主框架
        main_frame = ttk.Frame(self.root, padding="15")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 标题
        title_label = ttk.Label(main_frame, text="可视化拖拽测量尺", 
                               font=("微软雅黑", 14, "bold"))
        title_label.pack(pady=5)
        
        # 比例尺设置
        scale_frame = ttk.LabelFrame(main_frame, text="比例尺设置", padding="10")
        scale_frame.pack(fill=tk.X, pady=10)
        
        # 比例尺说明
        scale_help = ttk.Label(scale_frame, text="例如: 图纸上1cm=100像素，则输入100", 
                              font=("微软雅黑", 8), foreground="gray")
        scale_help.grid(row=0, column=0, columnspan=3, sticky=tk.W, pady=(0,5))
        
        ttk.Label(scale_frame, text="比例 (像素/单位):").grid(row=1, column=0, padx=5)
        self.scale_entry = ttk.Entry(scale_frame, width=15)
        self.scale_entry.insert(0, "100")
        self.scale_entry.grid(row=1, column=1, padx=5)
        
        ttk.Button(scale_frame, text="设置", 
                  command=self.set_scale).grid(row=1, column=2, padx=10)
        
        # 线条样式设置
        style_frame = ttk.LabelFrame(main_frame, text="线条样式", padding="5")
        style_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(style_frame, text="颜色:").grid(row=0, column=0, padx=5)
        self.color_var = tk.StringVar(value="red")
        color_combo = ttk.Combobox(style_frame, textvariable=self.color_var, 
                                  values=["red", "blue", "green", "yellow", "white", "black"], 
                                  width=8, state="readonly")
        color_combo.grid(row=0, column=1, padx=5)
        color_combo.bind('<<ComboboxSelected>>', self.change_line_color)
        
        ttk.Label(style_frame, text="粗细:").grid(row=0, column=2, padx=5)
        self.width_var = tk.StringVar(value="2")
        width_combo = ttk.Combobox(style_frame, textvariable=self.width_var, 
                                  values=["1", "2", "3", "4", "5"], 
                                  width=5, state="readonly")
        width_combo.grid(row=0, column=3, padx=5)
        width_combo.bind('<<ComboboxSelected>>', self.change_line_width)
        
        # 按钮区域
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(pady=15)
        
        self.start_btn = ttk.Button(btn_frame, text="开始拖拽测量", 
                                   command=self.toggle_measurement,
                                   style="Accent.TButton")
        self.start_btn.pack(side=tk.LEFT, padx=10)
        
        ttk.Button(btn_frame, text="清空结果", 
                  command=self.clear_results).pack(side=tk.LEFT, padx=10)
        
        #ttk.Button(btn_frame, text="清除线段", 
                 # command=self.clear_lines).pack(side=tk.LEFT, padx=10)
        
        ttk.Button(btn_frame, text="退出", 
                  command=self.root.quit).pack(side=tk.LEFT, padx=10)
        
        # 状态显示
        self.status_label = ttk.Label(main_frame, text="状态: 就绪", 
                                     foreground="green", font=("微软雅黑", 10))
        self.status_label.pack(pady=5)
        
        # 结果显示
        result_frame = ttk.LabelFrame(main_frame, text="测量结果", padding="10")
        result_frame.pack(fill=tk.X, pady=10)
        
        self.result_text = tk.Text(result_frame, height=3, width=50, 
                                  font=("微软雅黑", 9), wrap=tk.WORD)
        scrollbar = ttk.Scrollbar(result_frame, orient=tk.VERTICAL, command=self.result_text.yview)
        self.result_text.configure(yscrollcommand=scrollbar.set)
        self.result_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.result_text.insert(tk.END, "暂无测量结果\n")
        self.result_text.config(state=tk.DISABLED)
        
        # 使用说明
        help_text = """使用说明:
1. 设置比例尺 (如: 图纸上1cm=100像素，则输入100)
2. 点击"开始拖拽测量"
3. 在屏幕上按住鼠标左键拖动进行测量
4. 拖拽时会显示测量线，松开左键完成测量
5. 所有测量线段会保持显示直到按下ESC键
6. 按ESC键结束测量模式并清除所有线段"""
        
        help_label = ttk.Label(main_frame, text=help_text, 
                              justify=tk.LEFT, font=("微软雅黑", 9))
        help_label.pack(pady=5)
        
        # 绑定ESC键
        self.root.bind('<Escape>', self.stop_measurement)
        
    def set_scale(self):
        try:
            self.scale_factor = float(self.scale_entry.get())
            if self.scale_factor <= 0:
                raise ValueError
            messagebox.showinfo("成功", f"比例尺已设置为: {self.scale_factor} 像素/单位")
        except ValueError:
            messagebox.showerror("错误", "请输入有效的正数")
            
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
            messagebox.showerror("错误", "请先设置有效的比例尺")
            return
            
        self.is_measuring = True
        self.start_btn.config(text="停止测量")
        self.status_label.config(text="状态: 测量中... 按住左键拖动测量", foreground="red")
        
        # 创建全屏透明窗口来捕获鼠标事件
        self.create_capture_window()
        
        # 创建实时显示窗口
        self.create_overlay_window()
        
        # 最小化主窗口
        self.root.iconify()
        
    def create_capture_window(self):
        """创建全屏透明窗口来捕获鼠标事件"""
        self.capture_window = tk.Toplevel(self.root)
        self.capture_window.attributes('-fullscreen', True)
        self.capture_window.attributes('-alpha', 0.3)  # 几乎透明
        self.capture_window.attributes('-topmost', True)
        self.capture_window.configure(cursor="crosshair", bg='black')
        
        # 创建画布用于绘制测量线
        self.canvas = tk.Canvas(self.capture_window, highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.canvas.configure(bg='black')
        
        # 绑定事件
        self.canvas.bind('<Button-1>', self.on_mouse_down)
        self.canvas.bind('<B1-Motion>', self.on_mouse_drag)
        self.canvas.bind('<ButtonRelease-1>', self.on_mouse_up)
        self.capture_window.bind('<Escape>', self.stop_measurement)
        
        # 初始化临时线条ID
        self.temp_line_id = None
        
    def create_overlay_window(self):
        """创建实时显示的小窗口"""
        self.overlay_window = tk.Toplevel(self.root)
        self.overlay_window.overrideredirect(True)  # 无边框
        self.overlay_window.attributes('-topmost', True)  # 置顶
        self.overlay_window.attributes('-alpha', 0.85)  # 透明度
        self.overlay_window.configure(bg='lightyellow')
        
        # 创建显示标签
        self.overlay_label = tk.Label(self.overlay_window, 
                                     text="按住左键拖动测量", 
                                     bg='lightyellow', 
                                     fg='black',
                                     font=("微软雅黑", 10, "bold"),
                                     padx=10, pady=5,
                                     relief=tk.SOLID,
                                     borderwidth=1)
        self.overlay_label.pack()
        
    def on_mouse_down(self, event):
        """鼠标按下事件"""
        if self.is_measuring:
            self.start_point = (event.x_root, event.y_root)
            self.dragging = True
            self.update_overlay("开始测量...", event.x_root, event.y_root)
            
    def on_mouse_drag(self, event):
        """鼠标拖动事件"""
        if self.is_measuring and self.dragging and self.start_point:
            current_point = (event.x_root, event.y_root)
            
            # 清除之前的临时线条
            if self.temp_line_id:
                self.canvas.delete(self.temp_line_id)
            
            # 绘制新临时线条
            self.temp_line_id = self.canvas.create_line(
                self.start_point[0], self.start_point[1],
                current_point[0], current_point[1],
                fill=self.line_color, width=self.line_width
            )
            
            # 计算距离
            distance = math.sqrt(
                (current_point[0] - self.start_point[0])**2 + 
                (current_point[1] - self.start_point[1])**2
            )
            real_distance = distance / self.scale_factor
            
            # 更新实时显示
            display_text = f"像素: {distance:.1f}\n实际: {real_distance:.2f}"
            self.update_overlay(display_text, event.x_root, event.y_root)
            
    def on_mouse_up(self, event):
        """鼠标释放事件"""
        if self.is_measuring and self.dragging and self.start_point:
            end_point = (event.x_root, event.y_root)
            
            # 计算最终距离
            distance = math.sqrt(
                (end_point[0] - self.start_point[0])**2 + 
                (end_point[1] - self.start_point[1])**2
            )
            real_distance = distance / self.scale_factor
            
            # 将临时线条转换为永久线条
            if self.temp_line_id:
                # 删除临时线条
                self.canvas.delete(self.temp_line_id)
                
                # 创建永久线条
                permanent_line_id = self.canvas.create_line(
                    self.start_point[0], self.start_point[1],
                    end_point[0], end_point[1],
                    fill=self.line_color, width=self.line_width
                )
                
                # 存储线条信息
                self.measurement_lines.append({
                    'line_id': permanent_line_id,
                    'start_point': self.start_point,
                    'end_point': end_point,
                    'pixel_distance': distance,
                    'real_distance': real_distance
                })
                
                self.temp_line_id = None
            
            # 记录结果
            self.record_result(distance, real_distance, self.start_point, end_point)
            
            # 更新显示
            self.update_overlay(f"实际: {real_distance:.2f}", event.x_root, event.y_root)
            
        self.dragging = False
        self.start_point = None
        
    def update_overlay(self, text, x, y):
        """更新实时显示窗口的位置和内容"""
        if self.overlay_window and self.overlay_label:
            self.overlay_label.config(text=text)
            # 将窗口定位在鼠标位置旁边
            self.overlay_window.geometry(f"+{x}+{y+20}")
            
    def stop_measurement(self, event=None):
        self.is_measuring = False
        self.dragging = False
        self.start_btn.config(text="开始拖拽测量")
        self.status_label.config(text="状态: 就绪", foreground="green")
        
        # 清除所有测量线段
        self.clear_lines()
        
        # 关闭捕获窗口
        if self.capture_window:
            self.capture_window.destroy()
            self.capture_window = None
            
        # 关闭实时显示窗口
        if self.overlay_window:
            self.overlay_window.destroy()
            self.overlay_window = None
            
        # 恢复主窗口
        self.root.deiconify()
        self.root.lift()
        
    def clear_results(self):
        self.result_text.config(state=tk.NORMAL)
        self.result_text.delete(1.0, tk.END)
        self.result_text.insert(tk.END, "暂无测量结果\n")
        self.result_text.config(state=tk.DISABLED)
        
    def clear_lines(self):
        """清除所有测量线段"""
        if self.canvas:
            # 清除临时线条
            if self.temp_line_id:
                self.canvas.delete(self.temp_line_id)
                self.temp_line_id = None
                
            # 清除所有永久线条
            for line_info in self.measurement_lines:
                self.canvas.delete(line_info['line_id'])
            
            # 清空线条列表
            self.measurement_lines = []
        
    def record_result(self, pixel_distance, real_distance, start_point, end_point):
        """记录测量结果到文本框"""
        self.result_text.config(state=tk.NORMAL)
        
        # 添加分隔线（如果不是第一条记录）
        if self.result_text.get(1.0, tk.END).strip() != "暂无测量结果":
            self.result_text.insert(tk.END, "-" * 50 + "\n")
        
        # 插入新结果
        result_str = (f"起点: ({start_point[0]}, {start_point[1]})\n"
                     f"终点: ({end_point[0]}, {end_point[1]})\n"
                     f"像素距离: {pixel_distance:.2f}\n"
                     f"实际长度: {real_distance:.2f}\n\n")
        
        self.result_text.insert(tk.END, result_str)
        self.result_text.see(tk.END)  # 滚动到最后
        self.result_text.config(state=tk.DISABLED)

def main():
   
    root = tk.Tk()
    app = PersistentVisualRuler(root)
    root.mainloop()

if __name__ == "__main__":
    main()