import { Button, Input } from "@heroui/react"
import type { Device } from "../api/schemas"
import { useState } from "react"
import { autoToastError } from "./toast"

export function EditDevice({
	device,
	onSave,
}: {
	device: Device
	onSave: (updatedDevice: {
		device_name: string
		device_uuid: string
	}) => void
}) {
	const [deviceName, setDeviceName] = useState(device.device_name ?? "")
	const [deviceSerial, setDeviceSerial] = useState(device.device_uuid ?? "")

	function handleSave() {
		if (!deviceName?.trim() || !deviceSerial?.trim()) {
			autoToastError("Device name and serial cannot be empty.", null)
			return
		}

		onSave({
			device_name: deviceName,
			device_uuid: deviceSerial,
		})
	}

	return (
		<div className="flex flex-col gap-4">
			<Input
				label="Device Name"
				placeholder="Enter device name..."
				labelPlacement="outside"
				size="lg"
				value={deviceName}
				onChange={(e) => setDeviceName(e.target.value)}
			/>
			<Input
				label="Device Serial"
				placeholder="Enter device serial..."
				labelPlacement="outside"
				size="lg"
				value={deviceSerial}
				onChange={(e) => setDeviceSerial(e.target.value)}
			/>
			<Button color="primary" onPress={handleSave}>
				Save
			</Button>
		</div>
	)
}
