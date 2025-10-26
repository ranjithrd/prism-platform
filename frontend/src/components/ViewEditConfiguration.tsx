import dayjs from "dayjs"
import type { Config } from "../api/schemas"
import { toTitleCase } from "../utils/humanize"
import { Button } from "@heroui/react"
import { ConfigDisplay } from "./ConfigDisplay"
import EditConfiguration from "./EditConfiguration"

export default function ViewEditConfiguration({
	configuration,
	showConfig,
	setShowConfig,
	editing,
	setEditing,
	onSave,
}: {
	configuration: Config
	showConfig: boolean
	setShowConfig: (show: boolean) => void
	editing: boolean
	setEditing: (editing: boolean) => void
	onSave?: (config: Config) => void
}) {
	if (editing)
		return (
			<>
				<h2 className="text-2xl font-bold">Edit Configuration</h2>
				<div className="h-4"></div>
				<EditConfiguration
					configuration={configuration}
					onSave={(config) => {
						onSave?.(config)
					}}
				/>
				<Button
					variant="bordered"
					className="mt-4"
					onPress={() => setEditing(false)}
				>
					Cancel
				</Button>
			</>
		)

	return (
		<>
			<div className="flex flex-col md:flex-row md:justify-between md:items-center [overflow-clip-margin:1rem]">
				<div className="flex flex-col gap-1">
					<div className="text-sm text-gray-600">
						Configuration {configuration.config_id}
					</div>
					<h1 className="text-3xl font-bold">
						{configuration.config_name}
					</h1>
					<p>
						Last updated{" "}
						{dayjs(configuration.updated_at).format("MMM DD YYYY")}{" "}
						| {configuration.default_duration} seconds |{" "}
						{toTitleCase(configuration.tracing_tool ?? "")}
					</p>
				</div>
				<Button
					color="primary"
					size="md"
					onPress={() => setEditing(!editing)}
				>
					Edit Configuration
				</Button>
			</div>
			<div className="h-4"></div>
			{configuration.config_text && (
				<>
					<Button
						variant="bordered"
						color="primary"
						className="w-min"
						onPress={() => setShowConfig(!showConfig)}
					>
						{showConfig ? "Hide" : "Show"} Configuration Options
					</Button>
					<div className="h-2"></div>
					{showConfig && (
						<ConfigDisplay text={configuration.config_text} />
					)}
				</>
			)}
		</>
	)
}
