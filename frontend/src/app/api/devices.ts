import { getRegisteredDevices as getMockRegisteredDevices } from "../data/mockDevices";
import type { ChatDeviceOption } from "../types/device";

export async function getRegisteredDevices(): Promise<ChatDeviceOption[]> {
  // TODO: Replace with GET /api/devices when backend is ready.
  return getMockRegisteredDevices();
}

