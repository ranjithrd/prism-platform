import { useMemo, useState } from "react"
import {
	createTraceV1ApiTracesPost,
	useGetTracesV1ApiTracesGet,
} from "../../api/api-client"
import { Layout } from "../../components/Layout"
import ResponsiveGrid from "../../components/ResponsiveGrid"
import TraceCard from "../../components/TraceCard"
import Fuse from "fuse.js"
import { type SrcApiTracesTraceWithDevice } from "../../api/schemas"
import {
	Button,
	Input,
	Modal,
	ModalBody,
	ModalContent,
	ModalHeader,
	useDisclosure,
} from "@heroui/react"
import { humanizeDate } from "../../utils/humanize"
import { ArrowUpTrayIcon } from "@heroicons/react/20/solid"
import AddTrace from "../../components/AddTrace"
import { autoToast } from "../../components/toast"

export default function AllTracesPage() {
	const { data: traces, isLoading, mutate } = useGetTracesV1ApiTracesGet()
	const { isOpen, onOpen, onClose } = useDisclosure()

	const [searchTerm, setSearchTerm] = useState<string>("")

	const filteredTraces = useMemo(() => {
		const fuse = new Fuse<SrcApiTracesTraceWithDevice>(traces || [], {
			keys: [
				{
					name: "trace_id",
					weight: 0.4,
				},
				{
					name: "trace_name",
					weight: 0.5,
				},
				{
					name: "device_name",
					weight: 0.5,
				},
				{
					name: "timestamp",
					weight: 0.5,
					getFn: (trace) => humanizeDate(trace.trace_timestamp, true),
				},
			],
			threshold: 0.4,
		})
		if (!searchTerm) return traces
		const results = fuse.search(searchTerm)
		return results.map((result) => result.item)
	}, [searchTerm, traces])

	function handleUploadTrace(onClose: () => void) {
		return async (data: {
			trace_name: string
			trace_file: Blob
			trace_timestamp: string
			device_id: string
			config_id?: string
		}) => {
			await autoToast(
				createTraceV1ApiTracesPost({
					trace_name: data.trace_name,
					trace_file: data.trace_file,
					trace_timestamp: data.trace_timestamp,
					device_id: data.device_id,
					configuration_id: data.config_id,
				}),
				{
					successText: "Trace uploaded successfully",
					errorText: "Failed to upload trace",
					loadingText: "Uploading trace...",
				}
			)
			await mutate()
			onClose()
		}
	}

	return (
		<Layout>
			<div className="flex flex-col gap-2 md:flex-row md:justify-between md:items-center">
				<h1 className="text-2xl font-bold">Traces</h1>
				<Button color="primary" onPress={onOpen}>
					<ArrowUpTrayIcon className="size-4" />
					Upload Trace
				</Button>
			</div>
			<div className="h-4"></div>
			<Input
				placeholder="Search traces..."
				value={searchTerm}
				onValueChange={setSearchTerm}
			/>
			<div className="h-4"></div>
			{isLoading && <p>Loading traces...</p>}
			{filteredTraces && filteredTraces.length === 0 && (
				<p>No traces found.</p>
			)}
			<ResponsiveGrid className="gap-4">
				{filteredTraces &&
					filteredTraces.length > 0 &&
					filteredTraces.map((trace) => (
						<TraceCard key={trace.trace_id} trace={trace} />
					))}
			</ResponsiveGrid>
			<Modal isOpen={isOpen} onClose={onClose}>
				<ModalContent>
					{(onClose) => (
						<>
							<ModalHeader>
								<h3 className="text-lg font-semibold">
									Upload Trace
								</h3>
							</ModalHeader>
							<ModalBody className="flex flex-col mb-4">
								<AddTrace onSave={handleUploadTrace(onClose)} />
							</ModalBody>
						</>
					)}
				</ModalContent>
			</Modal>
		</Layout>
	)
}
