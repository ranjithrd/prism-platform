import { Card, CardBody } from "@heroui/react"
import type { Config } from "../api/schemas"
import { toTitleCase } from "../utils/humanize"

export default function ChooseConfigCard({
	config,
	isChosen,
	setIsChosen,
}: {
	config: Config
	isChosen: boolean
	setIsChosen: (isChosen: boolean) => void
}) {
	return (
		<Card
			className={`p-2  ${isChosen ? "bg-sky-800 text-white" : ""}`}
			isPressable
			onPress={() => {
				setIsChosen(!isChosen)
			}}
		>
			<CardBody className="flex flex-col justify-center h-full gap-0">
				<p className="text-xl font-semibold">{config.config_name}</p>
				<p className="">
					{config.tracing_tool
						? toTitleCase(config.tracing_tool)
						: "Perfetto"}
				</p>
			</CardBody>
		</Card>
	)
}
