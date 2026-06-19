import { getRegisteredDevices as getMockRegisteredDevices } from "../data/mockDevices";
import type { ChatDeviceOption, DeviceDetailOption } from "../types/device";
import { apiGet } from "./client";

export async function getRegisteredDevices(): Promise<ChatDeviceOption[]> {
  // TODO: Replace with GET /api/devices when backend is ready.
  return getMockRegisteredDevices();
}

function toBackendDeviceId(deviceId?: string) {
  if (!deviceId) return "D001";
  if (deviceId.startsWith("D")) return deviceId;
  return "D001";
}

export async function getDeviceDetail(deviceId?: string, userId = "U001"): Promise<DeviceDetailOption> {
  const backendDeviceId = toBackendDeviceId(deviceId);
  const params = new URLSearchParams({ user_id: userId });
  return apiGet<DeviceDetailOption>(`/devices/${encodeURIComponent(backendDeviceId)}?${params.toString()}`);
}

