import { Button, Card, CardBody, CardFooter } from "@heroui/react"
import type { TraceWithDevice } from "../api/schemas"
import { humanizeDate } from "../utils/humanize"
import { ArrowRightIcon } from "@heroicons/react/20/solid"
import { Link } from "wouter"

export default function TraceCard({ trace }: { trace: TraceWithDevice }) {
	return (
		<Link href={`/traces/${trace.trace_id}`} className="w-full focus-none">
			<Card className="w-full h-full p-2" isPressable>
				<CardBody className="flex flex-col gap-0">
					<p className="text-lg font-semibold">{trace.trace_name}</p>
					<p className="">
						<b>Device:</b> {trace.device_name}
					</p>
					<p className="">
						<b>Timestamp:</b>{" "}
						{humanizeDate(trace.trace_timestamp, true)}
					</p>
				</CardBody>
				<CardFooter className="flex justify-end w-full">
					<Button
						isIconOnly
						aria-label="View Details"
						size="sm"
						color="primary"
					>
						<ArrowRightIcon className="size-4" />
					</Button>
				</CardFooter>
			</Card>
		</Link>
	)
}
