import { Card, CardBody } from "@heroui/react"
import type { Config } from "../api/schemas"
import { Link } from "wouter"
import { ArrowTopRightOnSquareIcon } from "@heroicons/react/20/solid"

export default function TakeTraceCard({ config }: { config?: Config }) {
	if (!config) {
		return (
			<Link to="/trace" className="w-full">
				<Card className="w-full h-full p-4" isPressable>
					<CardBody className="flex flex-col justify-end gap-0">
						<p className="text-xl font-semibold">
							<ArrowTopRightOnSquareIcon className="inline size-4" />{" "}
							Take a Trace
						</p>
					</CardBody>
				</Card>
			</Link>
		)
	}

	return (
		<Link
			to={`/trace?configuration_id=${config.config_id}`}
			className="w-full"
		>
			<Card className="w-full h-full p-4" isPressable>
				<CardBody className="flex flex-col justify-end gap-0">
					<p className="text-xl font-semibold">
						<ArrowTopRightOnSquareIcon className="inline size-4" />{" "}
						Take a Trace
					</p>
				</CardBody>
			</Card>
		</Link>
	)
}
