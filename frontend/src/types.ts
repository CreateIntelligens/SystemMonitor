export interface SystemInfo {
  hostname: string;
  platform: string;
  cpu_count: number;
  local_ip: string;
  gpu_name?: string;
  gpu_memory_total?: number;
}

export interface GPUInfo {
  gpu_id: number;
  gpu_name: string;
  gpu_usage: number | null;
  vram_used_mb: number | null;
  vram_total_mb: number | null;
  vram_usage: number | null;
  temperature: number | null;
  power_draw?: number;
  power_limit?: number;
  fan_speed?: number;
  clock_graphics?: number;
  clock_memory?: number;
  clock_sm?: number;
  pcie_gen?: number;
  pcie_width?: number;
  pcie_tx?: number;
  pcie_rx?: number;
  performance_state?: string;
}

export interface SystemStatus {
  cpu_usage: number;
  ram_usage: number;
  ram_used_gb: number;
  ram_total_gb: number;
  cpu_source: string;
  ram_source: string;
  gpu_available: boolean;
  gpu_list: GPUInfo[];
  system_info: SystemInfo;
  total_records: number;
  database_size_mb: number;
  earliest_record: string | null;
}

export interface ProcessInfo {
  pid: number;
  name: string;
  command: string;
  gpu_memory_mb: number;
  cpu_percent: number;
  ram_mb: number;
  start_time: string;
  status?: string;
  container_source?: string;
  gpu_utilization?: number;
  last_seen?: string;
  record_count?: number;
}

export interface ProcessResponse {
  current: ProcessInfo[];
  historical: ProcessInfo[];
}

export interface DatabaseInfo {
  filename: string;
  full_path: string;
  display_name: string;
  size_mb: number;
  is_current: boolean;
  year: number;
  week: number;
  start_date: string;
  end_date: string;
}

export interface DatabasesResponse {
  success: boolean;
  databases: DatabaseInfo[];
  current_database: string;
}

export interface ChartInfo {
  title: string;
  path: string;
}

export interface PlotResponse {
  success: boolean;
  charts?: ChartInfo[];
  error?: string;
  database?: string;
}
