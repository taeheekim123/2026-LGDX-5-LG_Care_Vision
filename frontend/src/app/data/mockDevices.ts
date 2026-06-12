import type { ChatDeviceOption } from "../types/device";

export function getRegisteredDevices(): ChatDeviceOption[] {
  return [
    { id: "1", name: "거실 에어컨", model: "LG 휘센 벽걸이" },
    { id: "2", name: "안방 에어컨", model: "LG 휘센 벽걸이" },
  ];
}

