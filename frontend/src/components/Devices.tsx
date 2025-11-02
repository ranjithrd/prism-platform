import {
	deleteDeviceV1ApiDevicesDeviceIdDeletePost,
	useGetDevicesV1ApiDevicesGet,
} from "../api/api-client"
import type { Device } from "../api/schemas"
import { toTitleCase } from "../utils/humanize"
import type { Column } from "./TableWrapper"
import TableWrapper from "./TableWrapper"
import { autoToast } from "./toast"

const columns = (
	refetch: () => void,
	onEdit?: (device: Device) => void
): Column<Device>[] =>
	[
		{
			key: "device_name",
			label: "Name",
		},
		{
			key: "device_uuid",
			label: "Serial Number",
			nullValue: "-",
		},
		{
			key: "host",
			label: "Connected Host",
			nullValue: "Disconnected",
		},
		{
			key: "last_status",
			label: "Status",
			render: (device) => toTitleCase(device.last_status) ?? "Disconnected",
			nullValue: "Disconnected",
		},
		onEdit && {
			key: "edit",
			label: "Edit",
			render: (_) => "Edit",
			onPress: (device: Device) => onEdit(device),
		},
		{
			key: "delete",
			label: "Delete",
			render: (_) => "Delete",
			onPress: (device: Device) => {
				const confirmed = window.confirm(
					`Are you sure you want to delete device ${device.device_name}? This action cannot be undone.`
				)
				if (!confirmed) return

				autoToast(
					deleteDeviceV1ApiDevicesDeviceIdDeletePost(
						device.device_id!
					),
					{
						loadingText: `Deleting device...`,
						successText: `Device deleted!`,
						errorText: `Failed to delete device.`,
					}
				).then(() => refetch())
			},
		},
	].filter((e) => !!e) as Column[]

export default function Devices({
	onEdit,
}: {
	onEdit?: (device: Device) => void
}) {
	const {
		data: devices,
		isLoading,
		mutate,
	} = useGetDevicesV1ApiDevicesGet({
		swr: {
			refreshInterval: 5000,
		},
	})

	if (isLoading) return <div>Loading...</div>

	return (
		<TableWrapper
			columns={columns(() => mutate(), onEdit)}
			data={devices || []}
			keyMethod={(d) => d.device_id}
		/>
	)
}
