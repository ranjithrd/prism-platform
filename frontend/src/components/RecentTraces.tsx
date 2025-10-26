import { useMemo } from "react"
import {
	useGetConfigurationTracesV1ApiConfigurationsConfigIdTracesGet,
	useGetTracesV1ApiTracesGet,
} from "../api/api-client"
import type { Config } from "../api/schemas"
import ResponsiveGrid from "./ResponsiveGrid"
import TakeTraceCard from "./TakeTraceCard"
import TraceCard from "./TraceCard"

export function RecentTracesByConfig({ config }: { config: Config }) {
	const { data: recentTraces, isLoading } =
		useGetConfigurationTracesV1ApiConfigurationsConfigIdTracesGet(
			config.config_id!
		)

	if (isLoading) {
		return <div>Loading recent traces...</div>
	}

	return (
		<ResponsiveGrid className="mt-4">
			{(recentTraces ?? []).map((trace) => (
				<TraceCard key={trace.trace_id} trace={trace} />
			))}
			<TakeTraceCard config={config} />
		</ResponsiveGrid>
	)
}

export function RecentTraces() {
	const { data: recentTraces, isLoading } = useGetTracesV1ApiTracesGet()

	const limitedTraces = useMemo(() => {
		return (recentTraces ?? []).slice(0, 3)
	}, [recentTraces])

	if (isLoading) {
		return <div>Loading recent traces...</div>
	}

	return (
		<ResponsiveGrid className="mt-4">
			{(limitedTraces ?? []).map((trace) => (
				<TraceCard key={trace.trace_id} trace={trace} />
			))}
			{/* <TakeTraceCard /> */}
		</ResponsiveGrid>
	)
}
