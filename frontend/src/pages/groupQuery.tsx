import { useSearchParams } from "wouter"
import {
	useGetConfigurationsV1ApiConfigurationsGet,
	useGetConfigurationTracesV1ApiConfigurationsConfigIdTracesGet,
} from "../api/api-client"
import { Layout } from "../components/Layout"
import { useEffect, useState } from "react"
import ResponsiveGrid from "../components/ResponsiveGrid"
import ChooseConfigCard from "../components/ChooseConfigCard"
import { ChooseTraces } from "../components/ChooseTraces"
import { InlineQueries } from "../components/InlineQueries"
import type { Query } from "../api/schemas"
import { autoToastError } from "../components/toast"
import { GroupQueryResult } from "../components/GroupQueryResult"

export default function GroupQueryPage() {
	const [params, setParams] = useSearchParams()
	const urlConfigId = params.get("configuration_id") ?? null

	const [selectedConfigId, setSelectedConfigId] = useState<string | null>(
		urlConfigId
	)
	const [numberTracesPerDevice, setNumberTracesPerDevice] = useState(3)
	const [selectedTraceIds, setSelectedTraceIds] = useState<string[]>([])
	const [query, setQuery] = useState<Query | null>(null)

	const { data: allConfigs, isLoading: allConfigsLoading } =
		useGetConfigurationsV1ApiConfigurationsGet({
			swr: {
				enabled: true,
			},
		})

	const { data: tracesForConfigData, isLoading: tracesForConfigLoading } =
		useGetConfigurationTracesV1ApiConfigurationsConfigIdTracesGet(
			selectedConfigId ?? "",
			{
				n: numberTracesPerDevice,
			},
			{
				swr: {
					enabled: selectedConfigId !== null,
				},
			}
		)

	async function handleRunQuery(query: Query) {
		if (selectedTraceIds.length === 0) {
			autoToastError(
				"Please select at least one trace to run the query.",
				null
			)
			return
		}

		setQuery(query)
	}

	function handleAutoSelect() {
		const groupedByDevice: { [deviceId: string]: string[] } = {}
		tracesForConfigData?.forEach((trace) => {
			if (!groupedByDevice[trace.device_id!]) {
				groupedByDevice[trace.device_id!] = []
			}
			groupedByDevice[trace.device_id!].push(trace.trace_id!)
		})

		const mostRecentTraceIds = Object.values(groupedByDevice).map(
			(traceIds) => traceIds[0]
		)

		setSelectedTraceIds(mostRecentTraceIds)
	}

	useEffect(() => {
		if (urlConfigId) {
			setSelectedConfigId(urlConfigId)
		}
	}, [urlConfigId])

	return (
		<Layout>
			<h1 className="text-2xl font-bold">Grouped Trace Analysis</h1>
			<p>
				Select a configuration and traces to analyze. Multiple traces
				can be selected for analysis, with exports containing metadata
				for each trace.
			</p>
			<div className="h-6"></div>
			<h2 className="text-xl font-bold">Choose a Configuration</h2>
			<div className="h-2"></div>
			{allConfigsLoading && <p>Loading configurations...</p>}
			<ResponsiveGrid>
				{(allConfigs ?? []).map((config) => (
					<ChooseConfigCard
						config={config}
						key={config.config_id ?? ""}
						isChosen={selectedConfigId === config.config_id!}
						setIsChosen={(isChosen) => {
							if (query) {
								setQuery(null)
							}
							if (isChosen) {
								setSelectedConfigId(config.config_id ?? "")
							} else {
								setSelectedConfigId(null)
							}
						}}
					/>
				))}
			</ResponsiveGrid>
			<div className="h-6"></div>
			<h2 className="text-xl font-bold">Choose Traces</h2>
			<p>
				Showing {numberTracesPerDevice} traces per device.{" "}
				<span className="underline text-primary-800">
					{numberTracesPerDevice < 5 ? (
						<button onClick={() => setNumberTracesPerDevice(10)}>
							Show more
						</button>
					) : (
						<button onClick={() => setNumberTracesPerDevice(3)}>
							Show less
						</button>
					)}
				</span>
			</p>
			<button
				className="text-left text-primary-800"
				onClick={handleAutoSelect}
			>
				Auto-select traces &rarr;
			</button>
			<div className="h-4"></div>
			{tracesForConfigLoading && <p>Loading traces...</p>}
			{tracesForConfigData && tracesForConfigData.length === 0 && (
				<p>No traces found for this configuration.</p>
			)}
			{!selectedConfigId && (
				<p>Please select a configuration to see traces.</p>
			)}
			<ChooseTraces
				traces={tracesForConfigData ?? []}
				isChosen={selectedTraceIds}
				setIsChosen={setSelectedTraceIds}
			/>
			<div className="h-6"></div>
			<InlineQueries
				showTitle
				configId={selectedConfigId}
				onRun={handleRunQuery}
			/>
			<div className="h-6"></div>
			{query && (
				<GroupQueryResult
					query={query}
					traceIds={selectedTraceIds.join(",")}
				/>
			)}
		</Layout>
	)
}
