import { Button, Card, CardBody, CardFooter, Chip, Link } from "@heroui/react"
import {
	useGetConfigurationTracesV1ApiConfigurationsConfigIdTracesGet,
	useGetJobRequestV1ApiRequestsJobIdGet,
} from "../api/api-client"
import { useJobResultStream, type StreamEvent } from "../api/streams"
import { Layout } from "../components/Layout"
import { humanizeDate } from "../utils/humanize"

const statuses = {
	pending: "Pending",
	running: "Running",
	starting: "Starting",
	completed: "Completed",
	failed: "Failed",
	partial: "Partial Success",
	uploading: "Uploading",
}

const statuses_colors: Record<
	string,
	"warning" | "primary" | "success" | "danger"
> = {
	pending: "warning",
	starting: "warning",
	running: "primary",
	completed: "success",
	failed: "danger",
	uploading: "primary",
	partial: "warning",
}

const statuses_text_colors: Record<string, "text-black" | "text-white"> = {
	pending: "text-black",
	starting: "text-black",
	running: "text-white",
	completed: "text-white",
	failed: "text-white",
	uploading: "text-white",
	partial: "text-black",
}

function ChipStatus({ status }: { status: string }) {
	return (
		<Chip
			color={statuses_colors[status]}
			size="sm"
			className={`-ml-1 uppercase text-xs font-bold  ${statuses_text_colors[status]}`}
		>
			{statuses[status as keyof typeof statuses]}
		</Chip>
	)
}

function JobStatusUpdate({ event }: { event: StreamEvent }) {
	return (
		<Card className="w-full p-4">
			<CardBody>
				{event.status?.length > 0 && (
					<ChipStatus status={event.status} />
				)}
				<p className="mt-1 font-bold">{event.device_serial}</p>
				{event.timestamp && (
					<p className="text-sm text-gray-600">
						{humanizeDate(event.timestamp, true)}
					</p>
				)}
				<div className="h-2"></div>
				<p>{event.message}</p>
			</CardBody>
			{event.trace_id && (
				<CardFooter className="flex justify-end w-full">
					<Link href={`/traces/${event.trace_id}`}>
						<Button color="primary" size="md">
							View Trace
						</Button>
					</Link>
				</CardFooter>
			)}
		</Card>
	)
}

export default function JobPage({ jobId }: { jobId: string }) {
	const { data: jobData, isLoading } = useGetJobRequestV1ApiRequestsJobIdGet(
		jobId,
		{
			swr: {
				refreshInterval: 5000,
			},
		}
	)
	const { stream, isConnected } = useJobResultStream(jobId)

	return (
		<Layout>
			<ChipStatus status={jobData?.status ?? "pending"} />
			<div className="h-4"></div>
			<p className="text-sm text-gray-600">Job {jobId}</p>
			<h1 className="text-3xl font-bold">
				Tracing on {jobData?.device_serials?.length ?? 0} device
				{jobData?.device_serials?.length === 1 ? "" : "s"} for{" "}
				{jobData?.duration ?? 0} seconds
			</h1>
			<p>Started on {humanizeDate(jobData?.created_at, true)}</p>
			<div className="h-2"></div>
			<p>{jobData?.result_summary ?? ""}</p>
			<div className="h-4"></div>
			<h2 className="text-2xl font-bold">Status Updates</h2>
			<div className="h-2"></div>
			{/* is connected */}
			{isConnected ? (
				<Chip
					color="success"
					size="sm"
					className="-ml-1 font-bold text-white uppercase"
				>
					Live Updates Connected
				</Chip>
			) : (
				<Chip
					color="danger"
					size="sm"
					className="-ml-1 font-bold text-white uppercase"
				>
					Live Updates Disconnected
				</Chip>
			)}
			<div className="h-4"></div>
			<div className="flex flex-col gap-4">
				{stream.map((event, index) => (
					<JobStatusUpdate key={index} event={event} />
				))}
			</div>
		</Layout>
	)
}
