import { useGetDevicesV1ApiDevicesGet } from "../api/api-client";

export function SelectDevices() {
    const { data: devices, isLoading } = useGetDevicesV1ApiDevicesGet()

    if (isLoading) {
        return <div>Loading devices...</div>
    }

    if (!devices || devices.length === 0) {
        return <div>No devices found.</div>
    }

    return (
        <select className="p-2 border border-gray-300 rounded">
            {devices.map((device) => (
                <option key={device.device_id} value={device.device_id}>
                    {device.device_name}
                </option>
            ))}
        </select>
    )
}