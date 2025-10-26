import {
	deleteHostV1ApiHostsHostIdDeletePost,
	useGetHostsV1ApiHostsGet,
} from "../api/api-client"
import { humanizeDate, toTitleCase } from "../utils/humanize"
import type { Column } from "./TableWrapper"
import TableWrapper from "./TableWrapper"
import { autoToast } from "./toast"

const columns = (refetch: () => void): Column[] => [
	{
		key: "host_name",
		label: "Hostname",
	},
	{
		key: "status",
		label: "Status",
		render: (host) => (host.status ? toTitleCase(host.status) : "Offline"),
		nullValue: "Offline",
	},
	{
		key: "lastSeen",
		label: "Last Seen",
		render: (host) => humanizeDate(host.last_seen, true),
	},
	{
		key: "delete",
		label: "Actions",
		render: (_) => "Delete",
		onPress: (host) => {
			const confirmed = window.confirm(
				`Are you sure you want to delete host ${host.host_name}? This action cannot be undone.`
			)
			if (!confirmed) return

			autoToast(deleteHostV1ApiHostsHostIdDeletePost(host.host_name), {
				loadingText: `Deleting host...`,
				successText: `Host deleted!`,
				errorText: `Failed to delete host.`,
			}).then(() => refetch())
		},
	},
]

export default function Hosts() {
	const {
		data: hosts,
		isLoading,
		mutate,
	} = useGetHostsV1ApiHostsGet({
		swr: {
			refreshInterval: 15000,
		},
	})

	if (isLoading) return <div>Loading...</div>

	return (
		<TableWrapper
			columns={columns(() => mutate())}
			data={hosts || []}
			keyMethod={(h) => h.host_name}
		/>
	)
}
