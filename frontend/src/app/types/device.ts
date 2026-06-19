export interface ChatDeviceOption {
  id: string;
  name: string;
  model: string;
}

export interface DeviceCareSummary {
  self_care_count: number;
  self_as_count: number;
  total_care_count?: number;
  recent_title?: string;
  recent_date?: string;
}

export interface DeviceDetailOption extends ChatDeviceOption {
  care_summary?: DeviceCareSummary;
}

