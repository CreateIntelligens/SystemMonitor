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
        
        with plt.style.context(self._dark_style_params):
            fig, axes = plt.subplots(2, 2, figsize=(16, 12))
            fig.suptitle(f'System Monitor Overview - {timespan}', fontsize=16, fontweight='bold')
            
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
                    ax.plot(df['datetime'], data, color=color, linewidth=2, alpha=0.8)
                    ax.fill_between(df['datetime'], data, alpha=0.3, color=color)
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

        with plt.style.context(self._dark_style_params):
            fig, ax = plt.subplots(1, 1, figsize=(14, 8))
            for key in ['cpu', 'ram', 'gpu', 'vram']:
                col_name = f'{key}_usage'
                if col_name in df.columns and df[col_name].notna().any():
                    ax.plot(df['datetime'], df[col_name].fillna(0), color=self.colors[key], linewidth=2, label=key.upper(), alpha=0.8)
            
            ax.set_title('System Resource Usage Comparison', fontsize=16, fontweight='bold')
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

        with plt.style.context(self._dark_style_params):
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10), sharex=True)
            if 'ram_used_gb' in df.columns and 'ram_total_gb' in df.columns:
                ax1.plot(df['datetime'], df['ram_used_gb'], color=self.colors['ram'], linewidth=2, label='Used')
                ax1.fill_between(df['datetime'], df['ram_used_gb'], alpha=0.3, color=self.colors['ram'])
            ax1.set_title('RAM Usage (GB)', fontweight='bold')
            ax1.set_ylabel('Memory (GB)')
            ax1.legend()
            ax1.grid(True, alpha=0.3)

            if 'vram_used_mb' in df.columns and df['vram_used_mb'].notna().any():
                vram_used_gb = df['vram_used_mb'].fillna(0) / 1024
                ax2.plot(df['datetime'], vram_used_gb, color=self.colors['vram'], linewidth=2, label='Used')
                ax2.fill_between(df['datetime'], vram_used_gb, alpha=0.3, color=self.colors['vram'])
            else:
                ax2.text(0.5, 0.5, 'VRAM Data Not Available', ha='center', va='center', transform=ax2.transAxes, fontsize=14, alpha=0.5)
            ax2.set_title('VRAM Usage (GB)', fontweight='bold')
            ax2.set_ylabel('Memory (GB)')
            ax2.set_xlabel('Time')
            ax2.legend()
            ax2.grid(True, alpha=0.3)
            self._format_xaxis(ax2, (df['datetime'].max() - df['datetime'].min()).total_seconds())
            plt.tight_layout()
            if output_path is None:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                output_path = self.subdirs['memory'] / f'memory_usage_{timestamp}.png'
            plt.savefig(output_path, dpi=150, bbox_inches='tight')
            plt.close()
        return str(output_path)

    def plot_usage_distribution(self, metrics: List[Dict], output_path: Optional[str] = None) -> str:
        df = self._prepare_data(metrics)
        if df.empty: raise ValueError("No data to plot")

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
            axes = axes.flatten()
            for i, (title, data) in enumerate(valid_plots.items()):
                axes[i].hist(data, bins=20, color=self.colors[title.lower()], alpha=0.7, edgecolor='#cccccc')
                axes[i].set_title(f'{title} Usage Distribution')
                axes[i].set_xlabel('Usage (%)')
                axes[i].set_ylabel('Frequency')
            for i in range(n_plots, len(axes)): axes[i].set_visible(False)
            plt.tight_layout()
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

        with plt.style.context(self._dark_style_params):
            fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(16, 18), sharex=True)
            fig.suptitle(f'Processes Comparison ({timespan})', fontsize=16, fontweight='bold')

            colors = plt.cm.viridis(np.linspace(0, 1, len(pids)))

            for i, pid in enumerate(pids):
                pid_data = df[df['pid'] == pid]
                if pid_data.empty:
                    continue
                
                process_name = pid_data['process_name'].iloc[0]
                label = f'PID {pid} ({process_name})'
                color = colors[i]

                ax1.plot(pid_data['timestamp'], pid_data['cpu_percent'], color=color, label=label, alpha=0.8)
                ax2.plot(pid_data['timestamp'], pid_data['ram_mb'] / 1024, color=color, label=label, alpha=0.8)
                ax3.plot(pid_data['timestamp'], pid_data['gpu_memory_mb'], color=color, label=label, alpha=0.8)

            ax1.set_title('CPU Usage Comparison')
            ax1.set_ylabel('CPU (%)')
            ax1.legend()
            ax1.grid(True, alpha=0.3)

            ax2.set_title('RAM Usage Comparison')
            ax2.set_ylabel('RAM (GB)')
            ax2.legend()
            ax2.grid(True, alpha=0.3)

            ax3.set_title('GPU Memory Usage Comparison')
            ax3.set_ylabel('GPU Memory (MB)')
            ax3.set_xlabel('Time')
            ax3.legend()
            ax3.grid(True, alpha=0.3)

            self._format_xaxis(ax3, (df['timestamp'].max() - df['timestamp'].min()).total_seconds())

            plt.tight_layout(rect=[0, 0, 1, 0.96])
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath = self.subdirs['process_timeline'] / f"proc_compare_{timestamp}.png"
            plt.savefig(filepath, dpi=150, bbox_inches='tight')
            plt.close()

        return str(filepath)