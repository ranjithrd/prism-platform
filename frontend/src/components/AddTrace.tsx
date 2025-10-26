import { useMemo, useState } from "react"
import {
	useGetConfigurationsV1ApiConfigurationsGet,
	useGetDevicesV1ApiDevicesGet,
} from "../api/api-client"
import { Button, Input } from "@heroui/react"
import StringSelect from "./StringSelect"
import type { Config } from "../api/schemas"
import dayjs from "dayjs"

const CONFIGURATION_NONE_VALUE = "_NONE_"

export default function AddTrace({
	onSave,
}: {
	onSave: (data: {
		trace_name: string
		trace_file: Blob
		trace_timestamp: string
		device_id: string
		config_id?: string
	}) => void
}) {
	const [name, setName] = useState("")
	const [file, setFile] = useState<File | null>(null)
	const [timestamp, setTimestamp] = useState<string>("")
	const [configurationId, setConfigurationId] = useState<string>(
		CONFIGURATION_NONE_VALUE
	)
	const [deviceId, setDeviceId] = useState<string>(CONFIGURATION_NONE_VALUE)

	const { data: configurations } =
		useGetConfigurationsV1ApiConfigurationsGet()

	const { data: devices } = useGetDevicesV1ApiDevicesGet()

	const detailedOptions = useMemo(() => {
		let opts = [[CONFIGURATION_NONE_VALUE, "No Configuration"]]
		for (const config of configurations || []) {
			opts.push([
				config.config_id ?? "",
				config.config_name ?? "Unnamed Configuration",
			])
		}
		return Object.fromEntries(opts)
	}, [configurations])

	const deviceOptions = useMemo(() => {
		let opts = []
		for (const device of devices || []) {
			opts.push([
				device.device_id ?? "",
				device.device_name ?? "Unnamed Device",
			])
		}
		return Object.fromEntries(opts)
	}, [devices])

	return (
		<div className="flex flex-col gap-4">
			<Input
				label="Trace Name"
				labelPlacement="outside"
				size="lg"
				placeholder="Enter trace name"
				value={name}
				onValueChange={setName}
			/>
			<Input
				label="Trace Timestamp"
				labelPlacement="outside"
				placeholder="Timestamp"
				size="lg"
				type="datetime-local"
				value={timestamp}
				onValueChange={setTimestamp}
			/>
			<StringSelect
				label="Configuration"
				detailedOptions={detailedOptions}
				value={configurationId}
				onValueChange={setConfigurationId}
			/>
			<StringSelect
				label="Device"
				detailedOptions={deviceOptions}
				value={deviceId}
				onValueChange={setDeviceId}
			/>
			<Input
				label="Trace File"
				labelPlacement="outside"
				size="lg"
				type="file"
				accept=".pftrace,.data,.txt,.trace,.pfdata"
				onChange={(e) => {
					if (e.target.files && e.target.files.length > 0) {
						setFile(e.target.files[0])
					} else {
						setFile(null)
					}
				}}
			/>
			<Button
				color="primary"
				disabled={
					!name ||
					!file ||
					!timestamp ||
					!deviceId ||
					deviceId === CONFIGURATION_NONE_VALUE
				}
				onPress={() => {
					if (
						name &&
						file &&
						timestamp &&
                        configurationId &&
						deviceId &&
						deviceId !== CONFIGURATION_NONE_VALUE
					) {
						onSave({
							trace_name: name,
							trace_file: file,
							trace_timestamp: dayjs(timestamp).toISOString(),
							device_id: deviceId,
							config_id:
								configurationId === CONFIGURATION_NONE_VALUE
									? undefined
									: configurationId,
						})
					}
				}}
				className="mt-2"
			>
				Upload Trace
			</Button>
		</div>
	)
}
