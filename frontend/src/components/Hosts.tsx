import {
	Modal,
	ModalBody,
	ModalContent,
	ModalHeader,
	useDisclosure,
} from "@heroui/react"
import {
	addHostV1ApiHostsPost,
	deleteHostV1ApiHostsHostIdDeletePost,
	generateKeyV1ApiHostsHostIdKeyPost,
	useGetHostsV1ApiHostsGet,
} from "../api/api-client"
import type { HostWithStatus } from "../api/schemas"
import { humanizeDate, toTitleCase } from "../utils/humanize"
import type { Column } from "./TableWrapper"
import TableWrapper from "./TableWrapper"
import { autoToast } from "./toast"
import { useState } from "react"
import CodeView from "./CodeView"
import AddHost from "./AddHost"

const columns = (
	refetch: () => void,
	onGenerateKey?: (host: HostWithStatus) => void
): Column<HostWithStatus>[] =>
	[
		{
			key: "host_name",
			label: "Hostname",
		},
		{
			key: "status",
			label: "Status",
			render: (host) =>
				host.status ? toTitleCase(host.status) : "Offline",
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

				autoToast(
					deleteHostV1ApiHostsHostIdDeletePost(host.host_name),
					{
						loadingText: `Deleting host...`,
						successText: `Host deleted!`,
						errorText: `Failed to delete host.`,
					}
				).then(() => refetch())
			},
		},
		onGenerateKey
			? {
					key: "generate",
					label: "Generate Key",
					render: (host: HostWithStatus) => {
						return host.host_type === "worker"
							? "Generate Key"
							: null
					},
					onPress: (host: HostWithStatus) => {
						if (host.host_type !== "worker") return
						onGenerateKey(host)
					},
			  }
			: null,
	].filter((e) => !!e)

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

	const { isOpen, onOpen, onClose } = useDisclosure()
	const [generatedKey, setGeneratedKey] = useState<string | null>(null)

	async function onGenerateKey(host: HostWithStatus) {
		const confirmed = window.confirm(
			`Generate a new host key for ${host.host_name}? This will invalidate any previously generated keys.`
		)
		if (!confirmed) return
		setGeneratedKey(null)
		const res = await autoToast(
			generateKeyV1ApiHostsHostIdKeyPost(host.host_name),
			{
				loadingText: "Generating host key...",
				successText: "Host key generated successfully.",
				errorText: "Failed to generate host key.",
			}
		)
		if (res.host_key) {
			setGeneratedKey(res.host_key || null)
			onOpen()
		} else {
			setGeneratedKey(null)
		}
	}

	function handleAdd(hostname: string, onCloseModal: () => void) {
		autoToast(addHostV1ApiHostsPost({ host_name: hostname }), {
			loadingText: "Adding host...",
			successText: "Host added successfully.",
			errorText: "Failed to add host.",
		}).then(() => {
			mutate()
			onCloseModal()
		})
	}

	if (isLoading) return <div>Loading...</div>

	return (
		<>
			<TableWrapper
				columns={columns(
					() => mutate(),
					(h) => onGenerateKey(h)
				)}
				data={hosts || []}
				keyMethod={(h) => h.host_name}
			/>
			<Modal isOpen={isOpen} onClose={onClose} title="Generate Host Key">
				<ModalContent>
					{(_) => (
						<>
							<ModalHeader>
								<h3 className="text-lg font-semibold">
									Generated Worker Key
								</h3>
							</ModalHeader>
							<ModalBody className="flex flex-col gap-2 mb-4">
								<p>
									Copy this key to set up a worker on your
									system. This key expires in 6 months:
								</p>
								<CodeView fullText={generatedKey || ""}>
									{generatedKey}
								</CodeView>
							</ModalBody>
						</>
					)}
				</ModalContent>
			</Modal>
			<AddHost onAdd={handleAdd} />
		</>
	)
}
