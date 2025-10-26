import { useMemo } from "react"
import type { SrcApiConfigurationsTraceWithDevice } from "../api/schemas"
import ResponsiveGrid from "./ResponsiveGrid"
import { Card, CardBody, CardHeader, Checkbox } from "@heroui/react"
import { humanizeDate } from "../utils/humanize"

interface DeviceTraceGroup {
	device_id: string
	device_name: string
	traces: SrcApiConfigurationsTraceWithDevice[]
}

function TraceGroupCard({
	traceGroup,
	isChosen,
	setIsChosen,
}: {
	traceGroup: DeviceTraceGroup
	isChosen: string[]
	setIsChosen: (isChosen: string[]) => void
}) {
	return (
		<Card className="w-full p-4">
			<CardHeader className="flex flex-col items-start">
				<p>Device</p>
				<h3 className="text-xl font-semibold">
					{traceGroup.device_name}
				</h3>
			</CardHeader>
			<CardBody className="flex flex-col gap-2">
				{traceGroup.traces.map((trace) => (
					<Checkbox
						key={trace.trace_id}
						className="w-full"
						isSelected={isChosen.includes(trace.trace_id!)}
						onValueChange={() => {
							if (isChosen.includes(trace.trace_id!)) {
								setIsChosen(
									isChosen.filter(
										(id) => id !== trace.trace_id!
									)
								)
							} else {
								setIsChosen([...isChosen, trace.trace_id!])
							}
						}}
					>
						Trace from {humanizeDate(trace.trace_timestamp, true)}
					</Checkbox>
				))}
			</CardBody>
		</Card>
	)
}

export function ChooseTraces({
	traces,
	isChosen,
	setIsChosen,
}: {
	traces: SrcApiConfigurationsTraceWithDevice[]
	isChosen: string[]
	setIsChosen: (isChosen: string[]) => void
}) {
	const processedTraceGroups = useMemo(() => {
		const groups: DeviceTraceGroup[] = []
		traces.forEach((trace) => {
			const existingGroup = groups.find(
				(group) => group.device_id === trace.device_id
			)
			if (existingGroup) {
				existingGroup.traces.push(trace)
			} else {
				groups.push({
					device_id: trace.device_id,
					device_name: trace.device_name,
					traces: [trace],
				})
			}
		})
		return groups
	}, [traces])

	return (
		<div className="flex flex-col gap-2">
			<ResponsiveGrid size="large">
				{processedTraceGroups.map((group) => (
					<TraceGroupCard
						key={group.device_id}
						traceGroup={group}
						isChosen={isChosen}
						setIsChosen={setIsChosen}
					/>  
				))}
			</ResponsiveGrid>
		</div>
	)
}
