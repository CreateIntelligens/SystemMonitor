#!/usr/bin/env python3
"""
系統監控數據可視化模塊
使用 matplotlib 生成各種圖表
"""

import matplotlib
matplotlib.use('Agg')  # 使用非互動後端
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd
import numpy as np
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

# 設定字體
plt.rcParams['font.sans-serif'] = ['DejaVu Sans', 'Arial']
plt.rcParams['axes.unicode_minus'] = False

class SystemMonitorVisualizer:
    """系統監控可視化器"""
    
    def __init__(self):
        self.colors = {
            'cpu': '#FF6B6B', 'ram': '#4ECDC4', 'gpu': '#45B7D1',
            'vram': '#96CEB4', 'temperature': '#FECA57'
        }
        self.output_dir = Path('plots')
        self.output_dir.mkdir(exist_ok=True)
        self.subdirs = {k: self.output_dir / k for k in 
                        ['overview', 'comparison', 'memory', 'distribution', 'process_timeline']}
        for subdir in self.subdirs.values():
            subdir.mkdir(exist_ok=True)

        # **新增**：定義深色主題樣式
        self._dark_style_params = {
            'figure.facecolor': '#2c2f33',
            'axes.facecolor': '#2c2f33',
            'axes.edgecolor': '#555555',
            'axes.labelcolor': '#f0f0f0',
            'axes.titlecolor': '#f0f0f0',
            'xtick.color': '#f0f0f0',
            'ytick.color': '#f0f0f0',
            'grid.color': '#555555',
            'text.color': '#f0f0f0',
            'legend.facecolor': '#3c3f41',
            'legend.edgecolor': '#555555',
            'legend.labelcolor': '#f0f0f0'
        }

    def _prepare_data(self, metrics: List[Dict]) -> pd.DataFrame:
        if not metrics:
            return pd.DataFrame()
        df = pd.DataFrame(metrics)
        df['datetime'] = pd.to_datetime(df['timestamp'])
        return df.sort_values('datetime').reset_index(drop=True)

    def _format_xaxis(self, ax, time_span_seconds):
        if time_span_seconds <= 3600: # 1小時內
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
            ax.xaxis.set_major_locator(mdates.MinuteLocator(interval=max(1, int(time_span_seconds/600))))
        elif time_span_seconds <= 86400: # 1天內
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
            ax.xaxis.set_major_locator(mdates.HourLocator(interval=max(1, int(time_span_seconds/21600))))
        else: # 超過1天
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d %H:%M'))
            ax.xaxis.set_major_locator(mdates.HourLocator(interval=max(6, int(time_span_seconds/43200))))
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')

    def plot_system_overview(self, metrics: List[Dict], output_path: Optional[str] = None, timespan: str = "24h") -> str:
        df = self._prepare_data(metrics)
        if df.empty: raise ValueError("No data to plot")
        
        # 獲取實際的時間範圍
        start_time = df['datetime'].min().strftime('%m/%d %H:%M')
        end_time = df['datetime'].max().strftime('%m/%d %H:%M')
        date_range = f"{start_time} - {end_time}"
        
        with plt.style.context(self._dark_style_params):
            fig, axes = plt.subplots(2, 2, figsize=(16, 12))
            fig.suptitle(f'System Monitor Overview - {timespan}\n{date_range}', fontsize=16, fontweight='bold')
            
            axes_map = {
                'CPU Usage (%)': (df['cpu_usage'], self.colors['cpu']),
                'RAM Usage (%)': (df['ram_usage'], self.colors['ram']),
                'GPU Usage (%)': (df.get('gpu_usage'), self.colors['gpu']),
                'VRAM Usage (%)': (df.get('vram_usage'), self.colors['vram'])
            }

            for ax, (title, (data, color)) in zip(axes.flat, axes_map.items()):
                ax.set_title(title, fontweight='bold')
                ax.set_ylabel('Usage (%)')
                ax.grid(True, alpha=0.3)
                ax.set_ylim(0, 100)
                if data is not None and data.notna().any():
                    # 只繪製有數據的點，不連接缺失值
                    valid_mask = data.notna()
                    valid_times = df['datetime'][valid_mask]
                    valid_data = data[valid_mask]
                    
                    # 繪製散點圖（主要）
                    ax.scatter(valid_times, valid_data, color=color, s=20, alpha=0.8, zorder=3)
                    
                    # 只在連續數據點之間添加淡線連接（可選）
                    if len(valid_data) > 1:
                        ax.plot(valid_times, valid_data, color=color, linewidth=1, alpha=0.4, zorder=2)
                else:
                    ax.text(0.5, 0.5, 'Not Available', ha='center', va='center', transform=ax.transAxes, fontsize=14, alpha=0.5)
                self._format_xaxis(ax, (df['datetime'].max() - df['datetime'].min()).total_seconds())

            plt.tight_layout(rect=[0, 0, 1, 0.96])
            if output_path is None:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                output_path = self.subdirs['overview'] / f'system_overview_{timestamp}.png'
            plt.savefig(output_path, dpi=150, bbox_inches='tight')
            plt.close()
        return str(output_path)

    def plot_resource_comparison(self, metrics: List[Dict], output_path: Optional[str] = None) -> str:
        df = self._prepare_data(metrics)
        if df.empty: raise ValueError("No data to plot")

        # 獲取實際的時間範圍
        start_time = df['datetime'].min().strftime('%m/%d %H:%M')
        end_time = df['datetime'].max().strftime('%m/%d %H:%M')
        date_range = f"{start_time} - {end_time}"

        with plt.style.context(self._dark_style_params):
            fig, ax = plt.subplots(1, 1, figsize=(14, 8))
            for key in ['cpu', 'ram', 'gpu', 'vram']:
                col_name = f'{key}_usage'
                if col_name in df.columns and df[col_name].notna().any():
                    # 只繪製有數據的點，不連接缺失值
                    valid_mask = df[col_name].notna()
                    valid_times = df['datetime'][valid_mask]
                    valid_data = df[col_name][valid_mask]
                    
                    # 繪製散點圖（主要）
                    ax.scatter(valid_times, valid_data, color=self.colors[key], s=15, alpha=0.8, zorder=3, label=key.upper())
                    
                    # 只在連續數據點之間添加淡線連接（可選）
                    if len(valid_data) > 1:
                        ax.plot(valid_times, valid_data, color=self.colors[key], linewidth=1, alpha=0.4, zorder=2)
            
            ax.set_title(f'System Resource Usage Comparison\n{date_range}', fontsize=16, fontweight='bold')
            ax.set_ylabel('Usage (%)', fontsize=12)
            ax.set_xlabel('Time', fontsize=12)
            ax.grid(True, alpha=0.3)
            ax.legend(fontsize=11)
            ax.set_ylim(0, 100)
            self._format_xaxis(ax, (df['datetime'].max() - df['datetime'].min()).total_seconds())
            plt.tight_layout()
            if output_path is None:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                output_path = self.subdirs['comparison'] / f'resource_comparison_{timestamp}.png'
            plt.savefig(output_path, dpi=150, bbox_inches='tight')
            plt.close()
        return str(output_path)

    def plot_memory_usage(self, metrics: List[Dict], output_path: Optional[str] = None) -> str:
        df = self._prepare_data(metrics)
        if df.empty: raise ValueError("No data to plot")

        # 獲取實際的時間範圍
        start_time = df['datetime'].min().strftime('%m/%d %H:%M')
        end_time = df['datetime'].max().strftime('%m/%d %H:%M')
        date_range = f"{start_time} - {end_time}"

        with plt.style.context(self._dark_style_params):
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10), sharex=True)
            fig.suptitle(f'Memory Usage Overview\n{date_range}', fontsize=16, fontweight='bold')
            
            # RAM 圖表
            if 'ram_used_gb' in df.columns and 'ram_total_gb' in df.columns:
                # 只繪製有數據的點，不連接缺失值
                valid_mask = df['ram_used_gb'].notna()
                valid_times = df['datetime'][valid_mask]
                valid_data = df['ram_used_gb'][valid_mask]
                
                if len(valid_data) > 0:
                    # 繪製散點圖（主要）
                    ax1.scatter(valid_times, valid_data, color=self.colors['ram'], s=15, alpha=0.8, zorder=3, label='Used')
                    
                    # 只在連續數據點之間添加淡線連接和填充（可選）
                    if len(valid_data) > 1:
                        ax1.plot(valid_times, valid_data, color=self.colors['ram'], linewidth=1, alpha=0.4, zorder=2)
                        ax1.fill_between(valid_times, valid_data, alpha=0.2, color=self.colors['ram'])
                
                # 添加記憶體上限線
                total_ram = df['ram_total_gb'].iloc[0] if 'ram_total_gb' in df.columns else 16.0
                ax1.axhline(y=total_ram, color='red', linestyle='--', alpha=0.7, 
                           label=f'Total Memory ({total_ram:.1f}GB)')
                ax1.set_ylim(0, total_ram * 1.1)  # 給上限留點空間
                
            ax1.set_title('RAM Usage (GB)', fontweight='bold')
            ax1.set_ylabel('Memory (GB)')
            ax1.legend()
            ax1.grid(True, alpha=0.3)

            # VRAM 圖表  
            if 'vram_used_mb' in df.columns and df['vram_used_mb'].notna().any():
                # 只繪製有數據的點，不連接缺失值
                valid_mask = df['vram_used_mb'].notna()
                valid_times = df['datetime'][valid_mask]
                valid_data_mb = df['vram_used_mb'][valid_mask]
                valid_data_gb = valid_data_mb / 1024
                
                if len(valid_data_gb) > 0:
                    # 繪製散點圖（主要）
                    ax2.scatter(valid_times, valid_data_gb, color=self.colors['vram'], s=15, alpha=0.8, zorder=3, label='Used')
                    
                    # 只在連續數據點之間添加淡線連接和填充（可選）
                    if len(valid_data_gb) > 1:
                        ax2.plot(valid_times, valid_data_gb, color=self.colors['vram'], linewidth=1, alpha=0.4, zorder=2)
                        ax2.fill_between(valid_times, valid_data_gb, alpha=0.2, color=self.colors['vram'])
                
                # 添加VRAM上限線
                vram_total_for_chart = None
                if 'vram_total_mb' in df.columns:
                    vram_values = df['vram_total_mb'].dropna()
                    if len(vram_values) > 0 and vram_values.iloc[0] > 0:
                        vram_total_for_chart = vram_values.iloc[0] / 1024
                
                # 如果無法從資料中獲取，嘗試即時檢測
                if vram_total_for_chart is None:
                    try:
                        from .collectors import GPUCollector
                        gpu_collector = GPUCollector()
                        if gpu_collector.gpu_available:
                            gpu_stats = gpu_collector.get_gpu_stats()
                            if gpu_stats and len(gpu_stats) > 0:
                                vram_total_for_chart = gpu_stats[0].get('vram_total_mb', 0) / 1024
                    except:
                        pass
                
                # 最後預設值
                if vram_total_for_chart is None or vram_total_for_chart <= 0:
                    vram_total_for_chart = 12.0
                
                ax2.axhline(y=vram_total_for_chart, color='red', linestyle='--', alpha=0.7,
                           label=f'Total VRAM ({vram_total_for_chart:.1f}GB)')
                ax2.set_ylim(0, vram_total_for_chart * 1.1)
                    
            else:
                ax2.text(0.5, 0.5, 'VRAM Data Not Available', ha='center', va='center', transform=ax2.transAxes, fontsize=14, alpha=0.5)
            ax2.set_title('VRAM Usage (GB)', fontweight='bold')
            ax2.set_ylabel('Memory (GB)')
            ax2.set_xlabel('Time')
            ax2.legend()
            ax2.grid(True, alpha=0.3)
            self._format_xaxis(ax2, (df['datetime'].max() - df['datetime'].min()).total_seconds())
            plt.tight_layout(rect=[0, 0, 1, 0.94])
            if output_path is None:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                output_path = self.subdirs['memory'] / f'memory_usage_{timestamp}.png'
            plt.savefig(output_path, dpi=150, bbox_inches='tight')
            plt.close()
        return str(output_path)

    def plot_usage_distribution(self, metrics: List[Dict], output_path: Optional[str] = None) -> str:
        df = self._prepare_data(metrics)
        if df.empty: raise ValueError("No data to plot")

        # 獲取實際的時間範圍
        start_time = df['datetime'].min().strftime('%m/%d %H:%M')
        end_time = df['datetime'].max().strftime('%m/%d %H:%M')
        date_range = f"{start_time} - {end_time}"

        with plt.style.context(self._dark_style_params):
            plot_data = {
                'CPU': df['cpu_usage'].dropna(),
                'RAM': df['ram_usage'].dropna(),
                'GPU': df['gpu_usage'].dropna() if 'gpu_usage' in df.columns else None,
                'VRAM': df['vram_usage'].dropna() if 'vram_usage' in df.columns else None
            }
            valid_plots = {k: v for k, v in plot_data.items() if v is not None and not v.empty}
            n_plots = len(valid_plots)
            if n_plots == 0: raise ValueError("No data for distribution plot")

            fig, axes = plt.subplots((n_plots + 1) // 2, 2, figsize=(12, 6 * ((n_plots + 1) // 2)))
            fig.suptitle(f'Usage Distribution Analysis\n{date_range}', fontsize=16, fontweight='bold')
            axes = axes.flatten()
            for i, (title, data) in enumerate(valid_plots.items()):
                axes[i].hist(data, bins=20, color=self.colors[title.lower()], alpha=0.7, edgecolor='#cccccc')
                axes[i].set_title(f'{title} Usage Distribution')
                axes[i].set_xlabel('Usage (%)')
                axes[i].set_ylabel('Frequency')
            for i in range(n_plots, len(axes)): axes[i].set_visible(False)
            plt.tight_layout(rect=[0, 0, 1, 0.94])
            if output_path is None:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                output_path = self.subdirs['distribution'] / f'usage_distribution_{timestamp}.png'
            plt.savefig(output_path, dpi=150, bbox_inches='tight')
            plt.close()
        return str(output_path)

    def plot_process_timeline(self, process_data: List[Dict], process_name: str = "Unknown", timespan: str = "24h", group_by_pid: bool = True) -> str:
        if not process_data: raise ValueError("沒有進程數據可繪製")
        df = pd.DataFrame(process_data)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.sort_values('timestamp')

        with plt.style.context(self._dark_style_params):
            fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))
            fig.suptitle(f'Process Timeline: {process_name} ({timespan})', fontsize=16, fontweight='bold')
            
            pids = df['pid'].unique()[:6]
            colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FECA57', '#FF9FF3']
            
            for i, pid in enumerate(pids):
                pid_data = df[df['pid'] == pid]
                color, label = colors[i % len(colors)], f'PID {pid}'
                ax1.plot(pid_data['timestamp'], pid_data['gpu_memory_mb'], color=color, marker='o', markersize=3, label=label, alpha=0.8)
                ax2.plot(pid_data['timestamp'], pid_data['cpu_percent'], color=color, marker='s', markersize=3, label=label, alpha=0.8)
                ax3.plot(pid_data['timestamp'], pid_data['ram_mb'] / 1024, color=color, marker='^', markersize=3, label=label, alpha=0.8)

            ax1.set_title('GPU Memory Usage'); ax1.set_ylabel('GPU Memory (MB)')
            ax2.set_title('CPU Usage'); ax2.set_ylabel('CPU (%)')
            ax3.set_title('RAM Usage'); ax3.set_ylabel('RAM (GB)')
            for ax in [ax1, ax2, ax3]: ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left')

            process_count = df.groupby(df['timestamp'].dt.floor('5T')).size()
            ax4.bar(process_count.index, process_count.values, color='#96CEB4', alpha=0.7, width=0.003)
            ax4.set_title('Process Instances (5min intervals)'); ax4.set_ylabel('Process Count')

            for ax in fig.get_axes():
                ax.grid(True, alpha=0.3)
                ax.tick_params(axis='x', rotation=45)
                ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
                ax.xaxis.set_major_locator(mdates.HourLocator(interval=max(1, int((df['timestamp'].max() - df['timestamp'].min()).total_seconds() / 3600 / 8))))

            plt.tight_layout(rect=[0, 0, 0.85, 0.96])
            safe_name = "".join(c for c in process_name if c.isalnum()).rstrip()
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath = self.subdirs['process_timeline'] / f"process_{safe_name}_{timestamp}.png"
            plt.savefig(filepath, dpi=150, bbox_inches='tight')
            plt.close()
        return str(filepath)

    def plot_process_comparison(self, process_data: List[Dict], pids: List[int], timespan: str) -> str:
        """
        繪製多個指定PID的資源使用對比圖
        
        Args:
            process_data: 多個進程的數據列表
            pids: 用戶選擇的PID列表
            timespan: 時間範圍
            
        Returns:
            圖片檔案路徑
        """
        if not process_data:
            raise ValueError("沒有進程數據可繪製")

        df = pd.DataFrame(process_data)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.sort_values('timestamp')
        
        # 獲取系統記憶體上限資訊
        try:
            import psutil
            total_ram_gb = psutil.virtual_memory().total / (1024**3)
        except:
            # 備用方案：使用預設值
            total_ram_gb = 16.0
        
        # 嘗試從數據中獲取GPU記憶體上限
        total_vram_gb = None
        
        # 方法1: 從 raw_data 獲取
        if not df.empty and 'raw_data' in df.columns:
            try:
                import json
                for raw_data in df['raw_data'].dropna():
                    data = json.loads(raw_data)
                    if 'vram_total_mb' in data and data['vram_total_mb']:
                        total_vram_gb = data['vram_total_mb'] / 1024
                        break
            except:
                pass
        
        # 方法2: 從 vram_total_mb 欄位直接獲取
        if total_vram_gb is None and not df.empty and 'vram_total_mb' in df.columns:
            vram_values = df['vram_total_mb'].dropna()
            if len(vram_values) > 0 and vram_values.iloc[0] > 0:
                total_vram_gb = vram_values.iloc[0] / 1024
        
        # 方法3: 動態檢測目前系統 VRAM
        if total_vram_gb is None:
            try:
                from .collectors import GPUCollector
                gpu_collector = GPUCollector()
                if gpu_collector.gpu_available:
                    gpu_stats = gpu_collector.get_gpu_stats()
                    if gpu_stats and len(gpu_stats) > 0:
                        total_vram_gb = gpu_stats[0].get('vram_total_mb', 0) / 1024
            except:
                pass
        
        # 最後的預設值
        if total_vram_gb is None or total_vram_gb <= 0:
            total_vram_gb = 12.0  # 提高預設值，因為現代GPU通常有更多VRAM

        with plt.style.context(self._dark_style_params):
            fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(20, 16), sharex=True)
            fig.suptitle(f'Processes Comparison ({timespan})', fontsize=16, fontweight='bold')

            colors = plt.cm.viridis(np.linspace(0, 1, len(pids)))

            for i, pid in enumerate(pids):
                pid_data = df[df['pid'] == pid]
                if pid_data.empty:
                    continue
                
                process_name = pid_data['process_name'].iloc[0]
                label = f'PID {pid} ({process_name})'
                color = colors[i]

                # CPU 使用率 - 限制在 0-100% 範圍
                cpu_data = pid_data['cpu_percent'].clip(0, 100)
                ax1.plot(pid_data['timestamp'], cpu_data, color=color, label=label, alpha=0.8)
                
                # GPU 使用率 - 從原始數據中提取，如果有的話
                gpu_usage_data = None
                if 'raw_data' in pid_data.columns:
                    try:
                        import json
                        gpu_usage_list = []
                        for raw_data in pid_data['raw_data']:
                            if raw_data:
                                data = json.loads(raw_data)
                                gpu_usage = data.get('gpu_usage', 0) if isinstance(data, dict) else 0
                                gpu_usage_list.append(max(0, min(100, gpu_usage)))  # 限制在0-100%
                            else:
                                gpu_usage_list.append(0)
                        ax2.plot(pid_data['timestamp'], gpu_usage_list, color=color, label=label, alpha=0.8)
                    except:
                        ax2.plot(pid_data['timestamp'], [0] * len(pid_data), color=color, label=label, alpha=0.8)
                else:
                    ax2.plot(pid_data['timestamp'], [0] * len(pid_data), color=color, label=label, alpha=0.8)
                
                # RAM 使用量 - 轉換為 GB，確保非負值
                ram_data = (pid_data['ram_mb'] / 1024).clip(lower=0)
                ax3.plot(pid_data['timestamp'], ram_data, color=color, label=label, alpha=0.8)
                
                # GPU 記憶體 - 確保非負值，轉換為 GB
                gpu_memory_data = pid_data['gpu_memory_mb'].clip(lower=0) / 1024
                ax4.plot(pid_data['timestamp'], gpu_memory_data, color=color, label=label, alpha=0.8)

            # CPU 使用率圖表 (左上)
            ax1.set_title('CPU Usage Comparison')
            ax1.set_ylabel('CPU (%)')
            ax1.set_ylim(0, 100)  # CPU 使用率固定 0-100%
            ax1.legend()
            ax1.grid(True, alpha=0.3)

            # GPU 使用率圖表 (右上)
            ax2.set_title('GPU Usage Comparison') 
            ax2.set_ylabel('GPU (%)')
            ax2.set_ylim(0, 100)  # GPU 使用率固定 0-100%
            ax2.legend()
            ax2.grid(True, alpha=0.3)

            # RAM 使用量圖表 (左下)
            ax3.set_title('RAM Usage Comparison')
            ax3.set_ylabel('RAM (GB)')
            ax3.set_xlabel('Time')
            ax3.legend()
            ax3.grid(True, alpha=0.3)
            
            # 添加記憶體上限參考線
            ax3.axhline(y=total_ram_gb, color='red', linestyle='--', alpha=0.7, 
                       label=f'System Memory Limit ({total_ram_gb:.1f}GB)')
            ax3.legend()  # 重新設置圖例包含上限線
            
            # 設置Y軸範圍，確保從0開始
            max_ram_used = max([max((df[df['pid'] == pid]['ram_mb'] / 1024).clip(lower=0)) 
                               for pid in pids if not df[df['pid'] == pid].empty] + [1])
            ax3.set_ylim(0, max(total_ram_gb * 1.1, max_ram_used * 1.2))

            # GPU 記憶體使用圖表 (右下)
            ax4.set_title('GPU Memory Usage Comparison')
            ax4.set_ylabel('GPU Memory (GB)')
            ax4.set_xlabel('Time')
            
            # 添加GPU記憶體上限參考線
            ax4.axhline(y=total_vram_gb, color='red', linestyle='--', alpha=0.7, 
                       label=f'Total VRAM ({total_vram_gb:.1f}GB)')
            
            # 設置Y軸範圍，確保從0開始
            max_vram_used = max([max((df[df['pid'] == pid]['gpu_memory_mb'].clip(lower=0) / 1024)) 
                                for pid in pids if not df[df['pid'] == pid].empty] + [0.1])
            ax4.set_ylim(0, max(total_vram_gb * 1.1, max_vram_used * 1.2))
            
            ax4.legend()
            ax4.grid(True, alpha=0.3)

            # 格式化所有子圖的X軸
            time_span_seconds = (df['timestamp'].max() - df['timestamp'].min()).total_seconds()
            for ax in [ax1, ax2, ax3, ax4]:
                self._format_xaxis(ax, time_span_seconds)

            plt.tight_layout(rect=[0, 0, 1, 0.96])
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath = self.subdirs['process_timeline'] / f"proc_compare_{timestamp}.png"
            plt.savefig(filepath, dpi=150, bbox_inches='tight')
            plt.close()

        return str(filepath)