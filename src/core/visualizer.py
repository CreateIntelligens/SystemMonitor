#!/usr/bin/env python3
"""
系統監控數據可視化模塊
使用 matplotlib 生成各種圖表
"""

import matplotlib
matplotlib.use('Agg')  # 使用非互動後端
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.animation import FuncAnimation
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import threading
import time

# 設定字體 - 使用英文避免字體問題
plt.rcParams['font.sans-serif'] = ['DejaVu Sans', 'Arial']
plt.rcParams['axes.unicode_minus'] = False

# 設定圖表風格
plt.style.use('seaborn-v0_8' if 'seaborn-v0_8' in plt.style.available else 'default')


class SystemMonitorVisualizer:
    """系統監控可視化器"""
    
    def __init__(self):
        """初始化可視化器"""
        self.colors = {
            'cpu': '#FF6B6B',      # 紅色
            'ram': '#4ECDC4',      # 青色
            'gpu': '#45B7D1',      # 藍色
            'vram': '#96CEB4',     # 綠色
            'temperature': '#FECA57'  # 黃色
        }
        
        self.output_dir = Path('plots')
        self.output_dir.mkdir(exist_ok=True)
        
        # 創建子目錄
        self.subdirs = {
            'overview': self.output_dir / 'overview',
            'comparison': self.output_dir / 'comparison', 
            'memory': self.output_dir / 'memory',
            'distribution': self.output_dir / 'distribution',
            'processes': self.output_dir / 'processes'
        }
        
        # 創建所有子目錄
        for subdir in self.subdirs.values():
            subdir.mkdir(exist_ok=True)
    
    def _prepare_data(self, metrics: List[Dict]) -> pd.DataFrame:
        """
        準備數據為 DataFrame
        
        Args:
            metrics: 監控數據列表
            
        Returns:
            pandas DataFrame
        """
        if not metrics:
            return pd.DataFrame()
        
        # 轉換為 DataFrame
        df = pd.DataFrame(metrics)
        
        # 轉換時間戳
        df['datetime'] = pd.to_datetime(df['timestamp'])
        
        # 排序並重置索引
        df = df.sort_values('datetime').reset_index(drop=True)
        
        return df
    
    def plot_system_overview(self, metrics: List[Dict], 
                           output_path: Optional[str] = None,
                           timespan: str = "24h") -> str:
        """
        生成系統概覽圖表
        
        Args:
            metrics: 監控數據
            output_path: 輸出檔案路徑
            timespan: 時間範圍標題
            
        Returns:
            圖片檔案路徑
        """
        df = self._prepare_data(metrics)
        
        if df.empty:
            raise ValueError("No data to plot")
        
        # 創建子圖
        fig, axes = plt.subplots(2, 2, figsize=(16, 12))
        fig.suptitle(f'System Monitor Overview - {timespan}', fontsize=16, fontweight='bold')
        
        # CPU 使用率
        ax1 = axes[0, 0]
        ax1.plot(df['datetime'], df['cpu_usage'], 
                color=self.colors['cpu'], linewidth=2, alpha=0.8)
        ax1.fill_between(df['datetime'], df['cpu_usage'], 
                        alpha=0.3, color=self.colors['cpu'])
        ax1.set_title('CPU Usage (%)', fontweight='bold')
        ax1.set_ylabel('Usage (%)')
        ax1.grid(True, alpha=0.3)
        ax1.set_ylim(0, 100)
        
        # RAM 使用率
        ax2 = axes[0, 1]
        ax2.plot(df['datetime'], df['ram_usage'], 
                color=self.colors['ram'], linewidth=2, alpha=0.8)
        ax2.fill_between(df['datetime'], df['ram_usage'], 
                        alpha=0.3, color=self.colors['ram'])
        ax2.set_title('RAM Usage (%)', fontweight='bold')
        ax2.set_ylabel('Usage (%)')
        ax2.grid(True, alpha=0.3)
        ax2.set_ylim(0, 100)
        
        # GPU 使用率（如果有數據）
        ax3 = axes[1, 0]
        if 'gpu_usage' in df.columns and df['gpu_usage'].notna().any():
            gpu_data = df['gpu_usage'].fillna(0)
            ax3.plot(df['datetime'], gpu_data, 
                    color=self.colors['gpu'], linewidth=2, alpha=0.8)
            ax3.fill_between(df['datetime'], gpu_data, 
                            alpha=0.3, color=self.colors['gpu'])
            ax3.set_title('GPU Usage (%)', fontweight='bold')
            ax3.set_ylim(0, 100)
        else:
            ax3.text(0.5, 0.5, 'GPU Not Available', ha='center', va='center', 
                    transform=ax3.transAxes, fontsize=14, alpha=0.5)
            ax3.set_title('GPU Usage (%)', fontweight='bold')
        ax3.set_ylabel('Usage (%)')
        ax3.grid(True, alpha=0.3)
        
        # VRAM 使用率（如果有數據）
        ax4 = axes[1, 1]
        if 'vram_usage' in df.columns and df['vram_usage'].notna().any():
            vram_data = df['vram_usage'].fillna(0)
            ax4.plot(df['datetime'], vram_data, 
                    color=self.colors['vram'], linewidth=2, alpha=0.8)
            ax4.fill_between(df['datetime'], vram_data, 
                            alpha=0.3, color=self.colors['vram'])
            ax4.set_title('VRAM Usage (%)', fontweight='bold')
            ax4.set_ylim(0, 100)
        else:
            ax4.text(0.5, 0.5, 'VRAM Not Available', ha='center', va='center', 
                    transform=ax4.transAxes, fontsize=14, alpha=0.5)
            ax4.set_title('VRAM Usage (%)', fontweight='bold')
        ax4.set_ylabel('Usage (%)')
        ax4.grid(True, alpha=0.3)
        
        # 格式化 x 軸時間
        for ax in axes.flat:
            # 根據數據範圍選擇時間格式
            time_span = (df['datetime'].max() - df['datetime'].min()).total_seconds()
            
            if time_span <= 3600:  # 1小時內，顯示分:秒
                ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
                ax.xaxis.set_major_locator(mdates.MinuteLocator(interval=max(1, int(time_span/600))))
            elif time_span <= 86400:  # 1天內，顯示時:分
                ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
                ax.xaxis.set_major_locator(mdates.HourLocator(interval=max(1, int(time_span/21600))))
            else:  # 超過1天，顯示月-日 時:分
                ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d %H:%M'))
                ax.xaxis.set_major_locator(mdates.HourLocator(interval=max(6, int(time_span/43200))))
                
            plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')
            ax.tick_params(axis='x', labelsize=9)
            ax.tick_params(axis='y', labelsize=9)
        
        plt.tight_layout()
        
        # 儲存圖片
        if output_path is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_path = self.subdirs['overview'] / f'system_overview_{timestamp}.png'
        
        plt.savefig(output_path, dpi=300, bbox_inches='tight', 
                   facecolor='white', edgecolor='none')
        plt.close()
        
        return str(output_path)
    
    def plot_resource_comparison(self, metrics: List[Dict], 
                               output_path: Optional[str] = None) -> str:
        """
        生成資源使用率對比圖
        
        Args:
            metrics: 監控數據
            output_path: 輸出檔案路徑
            
        Returns:
            圖片檔案路徑
        """
        df = self._prepare_data(metrics)
        
        if df.empty:
            raise ValueError("No data to plot")
        
        fig, ax = plt.subplots(1, 1, figsize=(14, 8))
        
        # 繪製多條線
        ax.plot(df['datetime'], df['cpu_usage'], 
               color=self.colors['cpu'], linewidth=2, label='CPU', alpha=0.8)
        ax.plot(df['datetime'], df['ram_usage'], 
               color=self.colors['ram'], linewidth=2, label='RAM', alpha=0.8)
        
        if 'gpu_usage' in df.columns and df['gpu_usage'].notna().any():
            gpu_data = df['gpu_usage'].fillna(0)
            ax.plot(df['datetime'], gpu_data, 
                   color=self.colors['gpu'], linewidth=2, label='GPU', alpha=0.8)
        
        if 'vram_usage' in df.columns and df['vram_usage'].notna().any():
            vram_data = df['vram_usage'].fillna(0)
            ax.plot(df['datetime'], vram_data, 
                   color=self.colors['vram'], linewidth=2, label='VRAM', alpha=0.8)
        
        ax.set_title('System Resource Usage Comparison', fontsize=16, fontweight='bold')
        ax.set_ylabel('Usage (%)', fontsize=12)
        ax.set_xlabel('Time', fontsize=12)
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=11)
        ax.set_ylim(0, 100)
        
        # 格式化 x 軸
        time_span = (df['datetime'].max() - df['datetime'].min()).total_seconds()
        
        if time_span <= 3600:  # 1小時內
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
            ax.xaxis.set_major_locator(mdates.MinuteLocator(interval=max(1, int(time_span/600))))
        elif time_span <= 86400:  # 1天內
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
            ax.xaxis.set_major_locator(mdates.HourLocator(interval=max(1, int(time_span/21600))))
        else:  # 超過1天
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d %H:%M'))
            ax.xaxis.set_major_locator(mdates.HourLocator(interval=max(6, int(time_span/43200))))
            
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')
        ax.tick_params(axis='both', labelsize=10)
        
        plt.tight_layout()
        
        # 儲存圖片
        if output_path is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_path = self.subdirs['comparison'] / f'resource_comparison_{timestamp}.png'
        
        plt.savefig(output_path, dpi=300, bbox_inches='tight',
                   facecolor='white', edgecolor='none')
        plt.close()
        
        return str(output_path)
    
    def plot_memory_usage(self, metrics: List[Dict], 
                         output_path: Optional[str] = None) -> str:
        """
        生成記憶體使用詳細圖表
        
        Args:
            metrics: 監控數據
            output_path: 輸出檔案路徑
            
        Returns:
            圖片檔案路徑
        """
        df = self._prepare_data(metrics)
        
        if df.empty:
            raise ValueError("No data to plot")
        
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10))
        
        # RAM 使用情況
        if 'ram_used_gb' in df.columns and 'ram_total_gb' in df.columns:
            ax1.plot(df['datetime'], df['ram_used_gb'], 
                    color=self.colors['ram'], linewidth=2, label='Used')
            ax1.axhline(y=df['ram_total_gb'].iloc[-1], 
                       color='red', linestyle='--', alpha=0.7, label='Total')
            ax1.fill_between(df['datetime'], df['ram_used_gb'], 
                            alpha=0.3, color=self.colors['ram'])
        
        ax1.set_title('RAM Usage (GB)', fontweight='bold')
        ax1.set_ylabel('Memory (GB)')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # VRAM 使用情況（如果有數據）
        if ('vram_used_mb' in df.columns and 'vram_total_mb' in df.columns and 
            df['vram_used_mb'].notna().any()):
            
            vram_used_gb = df['vram_used_mb'].fillna(0) / 1024
            vram_total_gb = df['vram_total_mb'].fillna(0).iloc[-1] / 1024
            
            ax2.plot(df['datetime'], vram_used_gb, 
                    color=self.colors['vram'], linewidth=2, label='Used')
            ax2.axhline(y=vram_total_gb, 
                       color='red', linestyle='--', alpha=0.7, label='Total')
            ax2.fill_between(df['datetime'], vram_used_gb, 
                            alpha=0.3, color=self.colors['vram'])
            ax2.set_title('VRAM Usage (GB)', fontweight='bold')
        else:
            ax2.text(0.5, 0.5, 'VRAM Data Not Available', ha='center', va='center', 
                    transform=ax2.transAxes, fontsize=14, alpha=0.5)
            ax2.set_title('VRAM Usage (GB)', fontweight='bold')
        
        ax2.set_ylabel('Memory (GB)')
        ax2.set_xlabel('Time')
        ax2.legend()
        ax2.grid(True, alpha=0.3)
        
        # 格式化 x 軸
        time_span = (df['datetime'].max() - df['datetime'].min()).total_seconds()
        
        for ax in [ax1, ax2]:
            if time_span <= 3600:  # 1小時內
                ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
                ax.xaxis.set_major_locator(mdates.MinuteLocator(interval=max(1, int(time_span/600))))
            elif time_span <= 86400:  # 1天內
                ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
                ax.xaxis.set_major_locator(mdates.HourLocator(interval=max(1, int(time_span/21600))))
            else:  # 超過1天
                ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d %H:%M'))
                ax.xaxis.set_major_locator(mdates.HourLocator(interval=max(6, int(time_span/43200))))
                
            plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')
            ax.tick_params(axis='both', labelsize=10)
        
        plt.tight_layout()
        
        # 儲存圖片
        if output_path is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_path = self.subdirs['memory'] / f'memory_usage_{timestamp}.png'
        
        plt.savefig(output_path, dpi=300, bbox_inches='tight',
                   facecolor='white', edgecolor='none')
        plt.close()
        
        return str(output_path)
    
    def plot_usage_distribution(self, metrics: List[Dict], 
                              output_path: Optional[str] = None) -> str:
        """
        生成使用率分佈直方圖
        
        Args:
            metrics: 監控數據
            output_path: 輸出檔案路徑
            
        Returns:
            圖片檔案路徑
        """
        df = self._prepare_data(metrics)
        
        if df.empty:
            raise ValueError("No data to plot")
        
        # 計算子圖數量
        has_gpu = 'gpu_usage' in df.columns and df['gpu_usage'].notna().any()
        has_vram = 'vram_usage' in df.columns and df['vram_usage'].notna().any()
        
        n_plots = 2 + int(has_gpu) + int(has_vram)
        rows = (n_plots + 1) // 2
        
        fig, axes = plt.subplots(rows, 2, figsize=(12, 6 * rows))
        if n_plots <= 2:
            axes = axes.reshape(1, -1) if n_plots == 2 else [axes]
        
        axes = axes.flat
        
        # CPU 分佈
        axes[0].hist(df['cpu_usage'].dropna(), bins=20, 
                    color=self.colors['cpu'], alpha=0.7, edgecolor='black')
        axes[0].set_title('CPU Usage Distribution')
        axes[0].set_xlabel('Usage (%)')
        axes[0].set_ylabel('Frequency')
        axes[0].grid(True, alpha=0.3)
        
        # RAM 分佈
        axes[1].hist(df['ram_usage'].dropna(), bins=20, 
                    color=self.colors['ram'], alpha=0.7, edgecolor='black')
        axes[1].set_title('RAM Usage Distribution')
        axes[1].set_xlabel('Usage (%)')
        axes[1].set_ylabel('Frequency')
        axes[1].grid(True, alpha=0.3)
        
        plot_idx = 2
        
        # GPU 分佈
        if has_gpu:
            gpu_data = df['gpu_usage'].dropna()
            axes[plot_idx].hist(gpu_data, bins=20, 
                              color=self.colors['gpu'], alpha=0.7, edgecolor='black')
            axes[plot_idx].set_title('GPU Usage Distribution')
            axes[plot_idx].set_xlabel('Usage (%)')
            axes[plot_idx].set_ylabel('Frequency')
            axes[plot_idx].grid(True, alpha=0.3)
            plot_idx += 1
        
        # VRAM 分佈
        if has_vram:
            vram_data = df['vram_usage'].dropna()
            axes[plot_idx].hist(vram_data, bins=20, 
                              color=self.colors['vram'], alpha=0.7, edgecolor='black')
            axes[plot_idx].set_title('VRAM Usage Distribution')
            axes[plot_idx].set_xlabel('Usage (%)')
            axes[plot_idx].set_ylabel('Frequency')
            axes[plot_idx].grid(True, alpha=0.3)
            plot_idx += 1
        
        # 隱藏多餘的子圖
        for i in range(plot_idx, len(axes)):
            axes[i].set_visible(False)
        
        plt.tight_layout()
        
        # 儲存圖片
        if output_path is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_path = self.subdirs['distribution'] / f'usage_distribution_{timestamp}.png'
        
        plt.savefig(output_path, dpi=300, bbox_inches='tight',
                   facecolor='white', edgecolor='none')
        plt.close()
        
        return str(output_path)
    
    def generate_summary_stats(self, metrics: List[Dict]) -> Dict:
        """
        生成統計摘要
        
        Args:
            metrics: 監控數據
            
        Returns:
            統計摘要字典
        """
        df = self._prepare_data(metrics)
        
        if df.empty:
            return {}
        
        stats = {
            'data_points': len(df),
            'time_span': f"{df['datetime'].min()} - {df['datetime'].max()}",
            'cpu_stats': {
                'mean': round(df['cpu_usage'].mean(), 2),
                'max': round(df['cpu_usage'].max(), 2),
                'min': round(df['cpu_usage'].min(), 2),
                'std': round(df['cpu_usage'].std(), 2)
            },
            'ram_stats': {
                'mean': round(df['ram_usage'].mean(), 2),
                'max': round(df['ram_usage'].max(), 2),
                'min': round(df['ram_usage'].min(), 2),
                'std': round(df['ram_usage'].std(), 2)
            }
        }
        
        # 添加 GPU 統計（如果有數據）
        if 'gpu_usage' in df.columns and df['gpu_usage'].notna().any():
            gpu_data = df['gpu_usage'].dropna()
            stats['gpu_stats'] = {
                'mean': round(gpu_data.mean(), 2),
                'max': round(gpu_data.max(), 2),
                'min': round(gpu_data.min(), 2),
                'std': round(gpu_data.std(), 2)
            }
        
        # 添加 VRAM 統計（如果有數據）
        if 'vram_usage' in df.columns and df['vram_usage'].notna().any():
            vram_data = df['vram_usage'].dropna()
            stats['vram_stats'] = {
                'mean': round(vram_data.mean(), 2),
                'max': round(vram_data.max(), 2),
                'min': round(vram_data.min(), 2),
                'std': round(vram_data.std(), 2)
            }
        
        return stats


def main():
    """測試可視化功能"""
    print("📊 系統監控可視化測試")
    print("=" * 50)
    
    # 創建測試數據
    print("🔄 生成測試數據...")
    test_data = []
    base_time = datetime.now() - timedelta(hours=2)
    
    for i in range(120):  # 2小時的數據，每分鐘一筆
        timestamp = base_time + timedelta(minutes=i)
        
        test_data.append({
            'timestamp': timestamp.isoformat(),
            'unix_timestamp': timestamp.timestamp(),
            'cpu_usage': 30 + 40 * np.sin(i/10) + np.random.normal(0, 5),
            'ram_usage': 50 + 20 * np.sin(i/15) + np.random.normal(0, 3),
            'gpu_usage': 60 + 30 * np.sin(i/8) + np.random.normal(0, 8),
            'vram_usage': 40 + 35 * np.sin(i/12) + np.random.normal(0, 6),
            'ram_used_gb': 8.0 + 4.0 * np.sin(i/15),
            'ram_total_gb': 16.0,
            'vram_used_mb': 3200 + 2800 * np.sin(i/12),
            'vram_total_mb': 8192,
        })
    
    # 創建可視化器
    visualizer = SystemMonitorVisualizer()
    
    # 生成各種圖表
    print("📈 生成系統概覽圖...")
    overview_path = visualizer.plot_system_overview(test_data, timespan="2h")
    print(f"✅ 系統概覽圖: {overview_path}")
    
    print("📊 生成資源對比圖...")
    comparison_path = visualizer.plot_resource_comparison(test_data)
    print(f"✅ 資源對比圖: {comparison_path}")
    
    print("💾 生成記憶體使用圖...")
    memory_path = visualizer.plot_memory_usage(test_data)
    print(f"✅ 記憶體使用圖: {memory_path}")
    
    print("📊 生成使用率分佈圖...")
    distribution_path = visualizer.plot_usage_distribution(test_data)
    print(f"✅ 使用率分佈圖: {distribution_path}")
    
    # 生成統計摘要
    print("📋 生成統計摘要...")
    stats = visualizer.generate_summary_stats(test_data)
    print("統計摘要:")
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    print(f"\n✅ 可視化測試完成，圖片存儲在 plots/ 目錄")


if __name__ == "__main__":
    main()
