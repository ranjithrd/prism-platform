import { Button } from "@heroui/react"
import {
	deleteTraceV1ApiTracesTraceIdDeletePost,
	useGetTraceV1ApiTracesTraceIdGet,
} from "../../api/api-client"
import { InlineQueries } from "../../components/InlineQueries"
import { Layout } from "../../components/Layout"
import { toTitleCase } from "../../utils/humanize"
import { autoToast } from "../../components/toast"
import { useLocation } from "wouter"
import { QueryResult } from "../../components/QueryResult"
import { useState } from "react"
import type { Query } from "../../api/schemas"

export default function TracesViewPage({ id }: { id: string }) {
	const { data: trace, isLoading } = useGetTraceV1ApiTracesTraceIdGet(id)
	const [chosenQuery, setChosenQuery] = useState<Query | null>(null)
	const [, navigate] = useLocation()

	async function handleDelete() {
		const confirmed = window.confirm(
			"Are you sure you want to delete this trace? This action cannot be undone."
		)
		if (!confirmed) return

		await autoToast(deleteTraceV1ApiTracesTraceIdDeletePost(id), {
			loadingText: "Deleting trace...",
			successText: "Trace deleted!",
			errorText: "Failed to delete trace.",
		})

		navigate("/traces")
	}

	if (isLoading)
		return (
			<Layout>
				<p>Loading trace...</p>
			</Layout>
		)

	if (!trace)
		return (
			<Layout>
				<p>Trace not found!</p>
			</Layout>
		)

	return (
		<Layout>
			<p className="text-sm text-gray-600">Trace {trace.trace_id}</p>
			<h1 className="text-2xl font-bold">{trace.trace_name}</h1>
			<p>
				<b>Device</b> {trace.device_name} ({trace.host_name})
			</p>
			{trace.configuration_id && (
				<p>
					<b>Configuration</b> {trace.configuration_name} (
					{trace.configuration_type
						? toTitleCase(trace.configuration_type)
						: "Perfetto"}
					)
				</p>
			)}
			<div className="h-4"></div>
			<InlineQueries
				showTitle
				configId={trace.configuration_id}
				onRun={(query) => setChosenQuery(query)}
			/>
			<div className="h-4"></div>
			{chosenQuery && (
				<QueryResult query={chosenQuery} traceId={trace.trace_id} />
			)}
			<div className="h-4"></div>
			<Button
				variant="bordered"
				color="danger"
				className="w-min"
				onPress={handleDelete}
			>
				Delete Trace
			</Button>
		</Layout>
	)
}
