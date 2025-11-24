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

    def __init__(self, auto_cleanup: bool = True, max_age_days: int = 7):
        self.colors = {
            'cpu': '#FF6B6B', 'ram': '#4ECDC4', 'gpu': '#45B7D1',
            'vram': '#96CEB4', 'temperature': '#FECA57'
        }
        self.output_dir = Path('plots')
        self.output_dir.mkdir(exist_ok=True)

        self.max_age_days = max_age_days

        # 自動清理舊圖表
        if auto_cleanup:
            self.cleanup_old_plots()

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

    def cleanup_old_plots(self, max_age_days: Optional[int] = None) -> int:
        """
        清理超過指定天數的舊圖表

        Args:
            max_age_days: 保留天數（None 則使用初始化時的設定）

        Returns:
            刪除的文件數量
        """
        import time

        if max_age_days is None:
            max_age_days = self.max_age_days

        cutoff_time = time.time() - (max_age_days * 86400)  # 86400 秒 = 1 天
        deleted_count = 0

        try:
            # 清理所有 .png 文件
            for plot_file in self.output_dir.glob('*.png'):
                if plot_file.is_file() and plot_file.stat().st_mtime < cutoff_time:
                    plot_file.unlink()
                    deleted_count += 1

            if deleted_count > 0:
                print(f"🗑️  清理了 {deleted_count} 個超過 {max_age_days} 天的舊圖表")

        except Exception as e:
            print(f"❌ 清理圖表時發生錯誤: {e}")

        return deleted_count

    def _prepare_data(self, metrics: List[Dict], max_points: int = 1000) -> pd.DataFrame:
        if not metrics:
            return pd.DataFrame()
        df = pd.DataFrame(metrics)
        df['datetime'] = pd.to_datetime(df['timestamp'])
        df = df.sort_values('datetime').reset_index(drop=True)
        
        # 如果數據點過多，進行降採樣
        if len(df) > max_points:
            # 計算重採樣間隔
            time_span = df['datetime'].max() - df['datetime'].min()
            interval = time_span / max_points
            
            # 設置 datetime 為索引
            df.set_index('datetime', inplace=True)
            
            # 針對數值列進行重採樣（取平均值）
            numeric_cols = df.select_dtypes(include=[np.number]).columns
            
            # 對於非數值列（如 source），取第一個值
            # 這裡我們主要關心數值列的繪圖
            
            # 使用重採樣，保留峰值特徵可能更好，但平均值更平滑
            # 這裡我們使用平均值，因為這通常是趨勢圖的目的
            # 如果需要保留峰值，可以使用 .max() 或自定義聚合
            df_resampled = df[numeric_cols].resample(interval).mean()
            
            # 恢復 datetime 列
            df_resampled.reset_index(inplace=True)
            
            return df_resampled
            
        return df

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
            fig, axes = plt.subplots(1, 2, figsize=(16, 5))
            fig.suptitle(f'System Overview - {timespan}\n{date_range}', fontsize=16, fontweight='bold')

            time_span_seconds = (df['datetime'].max() - df['datetime'].min()).total_seconds()

            # 第一張圖：CPU + RAM (雙 Y 軸)
            ax_cpu = axes[0]
            ax_cpu.set_title('CPU & RAM Usage', fontweight='bold')
            ax_cpu.set_ylabel('CPU Usage (%)', color=self.colors['cpu'])
            ax_cpu.set_ylim(0, 100)
            ax_cpu.grid(True, alpha=0.3)
            ax_cpu.tick_params(axis='y', labelcolor=self.colors['cpu'])

            if 'cpu_usage' in df.columns and df['cpu_usage'].notna().any():
                valid = df['cpu_usage'].notna()
                ax_cpu.fill_between(df.loc[valid, 'datetime'], df.loc[valid, 'cpu_usage'], alpha=0.3, color=self.colors['cpu'])
                ax_cpu.plot(df.loc[valid, 'datetime'], df.loc[valid, 'cpu_usage'], color=self.colors['cpu'], linewidth=2, label='CPU %')

            # 第二個 Y 軸（RAM）
            ax_ram = ax_cpu.twinx()
            ax_ram.set_ylabel('RAM Usage (%)', color=self.colors['ram'])
            ax_ram.set_ylim(0, 100)
            ax_ram.tick_params(axis='y', labelcolor=self.colors['ram'])

            if 'ram_usage' in df.columns and df['ram_usage'].notna().any():
                valid = df['ram_usage'].notna()
                ax_ram.plot(df.loc[valid, 'datetime'], df.loc[valid, 'ram_usage'], color=self.colors['ram'], linewidth=2, linestyle='--', label='RAM %')

            self._format_xaxis(ax_cpu, time_span_seconds)

            # 第二張圖：GPU + VRAM (雙 Y 軸)
            ax_gpu = axes[1]
            ax_gpu.set_title('GPU & VRAM Usage', fontweight='bold')
            ax_gpu.set_ylabel('GPU Usage (%)', color=self.colors['gpu'])
            ax_gpu.set_ylim(0, 100)
            ax_gpu.grid(True, alpha=0.3)
            ax_gpu.tick_params(axis='y', labelcolor=self.colors['gpu'])

            if 'gpu_usage' in df.columns and df['gpu_usage'].notna().any():
                valid = df['gpu_usage'].notna()
                ax_gpu.fill_between(df.loc[valid, 'datetime'], df.loc[valid, 'gpu_usage'], alpha=0.3, color=self.colors['gpu'])
                ax_gpu.plot(df.loc[valid, 'datetime'], df.loc[valid, 'gpu_usage'], color=self.colors['gpu'], linewidth=2, label='GPU %')
            else:
                ax_gpu.text(0.5, 0.5, 'GPU Not Available', ha='center', va='center', transform=ax_gpu.transAxes, fontsize=14, alpha=0.5)

            # 第二個 Y 軸（VRAM）
            ax_vram = ax_gpu.twinx()
            ax_vram.set_ylabel('VRAM Usage (%)', color=self.colors['vram'])
            ax_vram.set_ylim(0, 100)
            ax_vram.tick_params(axis='y', labelcolor=self.colors['vram'])

            if 'vram_usage' in df.columns and df['vram_usage'].notna().any():
                valid = df['vram_usage'].notna()
                ax_vram.plot(df.loc[valid, 'datetime'], df.loc[valid, 'vram_usage'], color=self.colors['vram'], linewidth=2, linestyle='--', label='VRAM %')

            self._format_xaxis(ax_gpu, time_span_seconds)

            plt.tight_layout(rect=[0, 0, 1, 0.92])
            if output_path is None:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                output_path = self.output_dir / f'system_overview_{timestamp}.png'
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
                    valid_mask = df[col_name].notna()
                    valid_times = df['datetime'][valid_mask]
                    valid_data = df[col_name][valid_mask]

                    # 使用線條 + 淡填充
                    ax.plot(valid_times, valid_data, color=self.colors[key], linewidth=1.5, label=key.upper(), alpha=0.9)

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
                output_path = self.output_dir / f'resource_comparison_{timestamp}.png'
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
                valid_mask = df['ram_used_gb'].notna()
                valid_times = df['datetime'][valid_mask]
                valid_data = df['ram_used_gb'][valid_mask]

                if len(valid_data) > 0:
                    ax1.fill_between(valid_times, valid_data, alpha=0.3, color=self.colors['ram'])
                    ax1.plot(valid_times, valid_data, color=self.colors['ram'], linewidth=1.5, label='Used')

                # 添加記憶體上限線
                total_ram = df['ram_total_gb'].iloc[0] if 'ram_total_gb' in df.columns else 16.0
                ax1.axhline(y=total_ram, color='red', linestyle='--', alpha=0.7,
                           label=f'Total Memory ({total_ram:.1f}GB)')
                ax1.set_ylim(0, total_ram * 1.1)
                
            ax1.set_title('RAM Usage (GB)', fontweight='bold')
            ax1.set_ylabel('Memory (GB)')
            ax1.legend()
            ax1.grid(True, alpha=0.3)

            # VRAM 圖表
            if 'vram_used_mb' in df.columns and df['vram_used_mb'].notna().any():
                valid_mask = df['vram_used_mb'].notna()
                valid_times = df['datetime'][valid_mask]
                valid_data_mb = df['vram_used_mb'][valid_mask]
                valid_data_gb = valid_data_mb / 1024

                if len(valid_data_gb) > 0:
                    ax2.fill_between(valid_times, valid_data_gb, alpha=0.3, color=self.colors['vram'])
                    ax2.plot(valid_times, valid_data_gb, color=self.colors['vram'], linewidth=1.5, label='Used')
                
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
                output_path = self.output_dir / f'memory_usage_{timestamp}.png'
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
                output_path = self.output_dir / f'usage_distribution_{timestamp}.png'
            plt.savefig(output_path, dpi=150, bbox_inches='tight')
            plt.close()
        return str(output_path)

    def plot_process_timeline(self, process_data: List[Dict], process_name: str = "Unknown", timespan: str = "24h", group_by_pid: bool = True) -> str:
        if not process_data: raise ValueError("沒有進程數據可繪製")
        df = pd.DataFrame(process_data)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.sort_values('timestamp')

        # 限制顯示進程數量，避免 legend 過長
        all_pids = df['pid'].unique()
        display_pids = all_pids[:5]  # 只顯示前5個進程

        with plt.style.context(self._dark_style_params):
            fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))
            
            # 設定標題，如果有更多進程則顯示說明
            if len(all_pids) > 5:
                fig.suptitle(f'Process Timeline: {process_name} - Top 5 of {len(all_pids)} processes ({timespan})', fontsize=16, fontweight='bold')
            else:
                fig.suptitle(f'Process Timeline: {process_name} ({timespan})', fontsize=16, fontweight='bold')
            colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FECA57', '#FF9FF3']
            
            for i, pid in enumerate(display_pids):
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
            filepath = self.output_dir / f"process_{safe_name}_{timestamp}.png"
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

            # 限制顯示進程數量，避免 legend 過長
            display_pids = pids[:5]  # 只顯示前5個進程
            colors = plt.cm.viridis(np.linspace(0, 1, len(display_pids) + 1))  # +1 for total
            
            # 記錄總計數據
            total_cpu_data = None
            total_ram_data = None
            total_gpu_memory_data = None
            timestamps = None

            for i, pid in enumerate(display_pids):
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
                
                # 累加總計數據
                if timestamps is None:
                    timestamps = pid_data['timestamp']
                    total_cpu_data = cpu_data.copy()
                    total_ram_data = ram_data.copy()
                    total_gpu_memory_data = gpu_memory_data.copy()
                else:
                    # 對時間戳對齊並累加（簡化處理，假設時間戳相同）
                    if len(cpu_data) == len(total_cpu_data):
                        total_cpu_data += cpu_data
                        total_ram_data += ram_data
                        total_gpu_memory_data += gpu_memory_data
            
            # 繪製總計線（如果有多個進程）
            if len(display_pids) > 1 and timestamps is not None:
                total_color = colors[-1]  # 使用最後一個顏色
                ax1.plot(timestamps, total_cpu_data, color=total_color, label='Total CPU', 
                        linewidth=2, linestyle='--', alpha=1.0)
                ax3.plot(timestamps, total_ram_data, color=total_color, label='Total RAM', 
                        linewidth=2, linestyle='--', alpha=1.0)
                ax4.plot(timestamps, total_gpu_memory_data, color=total_color, label='Total GPU Memory', 
                        linewidth=2, linestyle='--', alpha=1.0)
            
            # 如果有被省略的進程，添加說明
            if len(pids) > 5:
                fig.suptitle(f'Processes Comparison - Top 5 of {len(pids)} selected ({timespan})', 
                           fontsize=16, fontweight='bold')

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
            filepath = self.output_dir / f"proc_compare_{timestamp}.png"
            plt.savefig(filepath, dpi=150, bbox_inches='tight')
            plt.close()

        return str(filepath)

    def plot_multi_gpu(self, gpu_metrics: List[Dict], gpu_ids: List[int] = None, timespan: str = "1h") -> str:
        """
        繪製多 GPU 圖表（總和 + 個別）

        Args:
            gpu_metrics: GPU 指標數據列表
            gpu_ids: 要顯示的 GPU ID 列表（None 表示全部）
            timespan: 時間範圍

        Returns:
            圖片檔案路徑
        """
        if not gpu_metrics:
            raise ValueError("沒有 GPU 數據可繪製")

        df = pd.DataFrame(gpu_metrics)
        df['datetime'] = pd.to_datetime(df['timestamp'])
        df = df.sort_values('datetime')

        # 獲取所有可用的 GPU ID
        available_gpus = sorted(df['gpu_id'].unique())

        # 如果未指定，使用所有 GPU
        if gpu_ids is None:
            gpu_ids = available_gpus
        else:
            gpu_ids = [g for g in gpu_ids if g in available_gpus]

        if not gpu_ids:
            raise ValueError("沒有有效的 GPU ID")

        # 獲取時間範圍
        start_time = df['datetime'].min().strftime('%m/%d %H:%M')
        end_time = df['datetime'].max().strftime('%m/%d %H:%M')
        date_range = f"{start_time} - {end_time}"

        # 計算總和/平均數據
        # 按時間分組計算
        df_filtered = df[df['gpu_id'].isin(gpu_ids)]

        # 解析 raw_data 中的 power_draw
        def get_power(row):
            raw = row.get('raw_data')
            if isinstance(raw, dict):
                return raw.get('power_draw')
            return None
        df_filtered = df_filtered.copy()
        df_filtered['power_draw'] = df_filtered.apply(get_power, axis=1)

        # 按時間戳分組計算總和/平均
        summary = df_filtered.groupby('datetime').agg({
            'gpu_usage': 'mean',      # 平均使用率
            'temperature': 'mean',     # 平均溫度
            'vram_used_mb': 'sum',     # 總 VRAM 使用量
            'vram_total_mb': 'first',  # VRAM 總量（取第一個）
            'power_draw': 'sum'        # 總功耗
        }).reset_index()

        # 計算總 VRAM 使用率
        total_vram_mb = df_filtered.groupby('datetime')['vram_total_mb'].sum().reset_index()
        summary['total_vram_usage'] = (summary['vram_used_mb'] / total_vram_mb['vram_total_mb'] * 100).fillna(0)

        n_gpus = len(gpu_ids)
        gpu_colors = plt.cm.tab10(np.linspace(0, 1, max(n_gpus, 10)))

        # 根據 GPU 數量調整標題
        if n_gpus == 1:
            title = f'GPU Monitor (GPU {gpu_ids[0]}) - {timespan}\n{date_range}'
        else:
            title = f'Multi-GPU Monitor ({n_gpus} GPUs) - {timespan}\n{date_range}'

        with plt.style.context(self._dark_style_params):
            # 計算佈局：上面 1 行總和，下面 2 行個別 GPU（4 列）
            n_rows = 3
            n_cols = 4
            fig = plt.figure(figsize=(20, 16))
            fig.suptitle(title, fontsize=16, fontweight='bold')

            # ===== 第一行：總和圖表 =====
            # GPU 使用率（單GPU顯示該GPU，多GPU顯示平均）
            ax_sum_usage = fig.add_subplot(n_rows, n_cols, 1)
            ax_sum_usage.fill_between(summary['datetime'], summary['gpu_usage'], alpha=0.3, color='#45B7D1')
            ax_sum_usage.plot(summary['datetime'], summary['gpu_usage'], color='#45B7D1', linewidth=2)
            usage_title = 'GPU Usage (%)' if n_gpus == 1 else 'Avg GPU Usage (%)'
            ax_sum_usage.set_title(usage_title, fontweight='bold')
            ax_sum_usage.set_ylim(0, 100)
            ax_sum_usage.grid(True, alpha=0.3)

            # 溫度（單GPU顯示該GPU，多GPU顯示平均）
            ax_sum_temp = fig.add_subplot(n_rows, n_cols, 2)
            ax_sum_temp.fill_between(summary['datetime'], summary['temperature'], alpha=0.3, color='#FECA57')
            ax_sum_temp.plot(summary['datetime'], summary['temperature'], color='#FECA57', linewidth=2)
            ax_sum_temp.axhline(y=80, color='orange', linestyle='--', alpha=0.7)
            temp_title = 'Temperature (°C)' if n_gpus == 1 else 'Avg Temperature (°C)'
            ax_sum_temp.set_title(temp_title, fontweight='bold')
            ax_sum_temp.grid(True, alpha=0.3)

            # VRAM 使用率（單GPU或多GPU都顯示總和）
            ax_sum_vram = fig.add_subplot(n_rows, n_cols, 3)
            ax_sum_vram.fill_between(summary['datetime'], summary['total_vram_usage'], alpha=0.3, color='#96CEB4')
            ax_sum_vram.plot(summary['datetime'], summary['total_vram_usage'], color='#96CEB4', linewidth=2)
            vram_title = 'VRAM Usage (%)' if n_gpus == 1 else 'Total VRAM Usage (%)'
            ax_sum_vram.set_title(vram_title, fontweight='bold')
            ax_sum_vram.set_ylim(0, 100)
            ax_sum_vram.grid(True, alpha=0.3)

            # 功耗（單GPU或多GPU都顯示總和）
            ax_sum_power = fig.add_subplot(n_rows, n_cols, 4)
            power_valid = summary['power_draw'].dropna()
            if len(power_valid) > 0:
                ax_sum_power.fill_between(summary['datetime'], summary['power_draw'].fillna(0), alpha=0.3, color='#FF6B6B')
                ax_sum_power.plot(summary['datetime'], summary['power_draw'].fillna(0), color='#FF6B6B', linewidth=2)
            power_title = 'Power (W)' if n_gpus == 1 else 'Total Power (W)'
            ax_sum_power.set_title(power_title, fontweight='bold')
            ax_sum_power.grid(True, alpha=0.3)

            # ===== 第二、三行：個別 GPU =====
            for i, gpu_id in enumerate(gpu_ids[:8]):  # 最多顯示 8 張
                gpu_data = df_filtered[df_filtered['gpu_id'] == gpu_id]
                if gpu_data.empty:
                    continue

                ax_idx = n_cols + i + 1  # 從第 5 個子圖開始
                ax = fig.add_subplot(n_rows, n_cols, ax_idx)

                color = gpu_colors[i]
                vram_color = '#96CEB4'  # VRAM 使用綠色

                # 繪製 GPU 使用率（左側 Y 軸）
                if 'gpu_usage' in gpu_data.columns:
                    valid = gpu_data['gpu_usage'].notna()
                    if valid.any():
                        ax.fill_between(gpu_data.loc[valid, 'datetime'],
                                       gpu_data.loc[valid, 'gpu_usage'],
                                       alpha=0.3, color=color)
                        ax.plot(gpu_data.loc[valid, 'datetime'],
                               gpu_data.loc[valid, 'gpu_usage'],
                               color=color, linewidth=2, label='GPU Usage')

                ax.set_title(f'GPU {gpu_id}', fontweight='bold', color=color)
                ax.set_ylim(0, 100)
                ax.set_ylabel('GPU Usage %', color=color)
                ax.tick_params(axis='y', labelcolor=color)
                ax.grid(True, alpha=0.3)

                # 繪製 VRAM 使用率（右側 Y 軸）
                ax2 = ax.twinx()
                if 'vram_used_mb' in gpu_data.columns and 'vram_total_mb' in gpu_data.columns:
                    vram_usage = (gpu_data['vram_used_mb'] / gpu_data['vram_total_mb'] * 100).fillna(0)
                    valid = vram_usage.notna()
                    if valid.any():
                        ax2.plot(gpu_data.loc[valid, 'datetime'],
                                vram_usage.loc[valid],
                                color=vram_color, linewidth=2, linestyle='--', label='VRAM Usage')

                ax2.set_ylim(0, 100)
                ax2.set_ylabel('VRAM %', color=vram_color)
                ax2.tick_params(axis='y', labelcolor=vram_color)

            # 格式化所有 X 軸
            time_span_seconds = (df['datetime'].max() - df['datetime'].min()).total_seconds()
            for ax in fig.get_axes():
                self._format_xaxis(ax, time_span_seconds)

            plt.tight_layout(rect=[0, 0, 1, 0.95])
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_path = self.output_dir / f'multi_gpu_{timestamp}.png'
            plt.savefig(output_path, dpi=150, bbox_inches='tight')
            plt.close()

        return str(output_path)
