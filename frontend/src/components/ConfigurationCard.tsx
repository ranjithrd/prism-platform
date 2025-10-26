import { Link } from "wouter"
import type { Config } from "../api/schemas"
import { Card, CardBody } from "@heroui/react"
import { humanizeDate, toTitleCase } from "../utils/humanize"

export default function ConfigurationCard({ config }: { config: Config }) {
	return (
		<Link to={`/configurations/${config.config_id}`}>
			<Card className="p-4 transition-shadow min-w-80">
				<CardBody>
					<h2 className="text-lg font-bold">{config.config_name}</h2>
					<p className="text-sm">
						{config.tracing_tool
							? toTitleCase(config.tracing_tool)
							: "Perfetto"}{" "}
						| Last updated {humanizeDate(config.updated_at, false)}
					</p>
				</CardBody>
			</Card>
		</Link>
	)
}
