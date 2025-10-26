import { useState } from "react"
import type { Config } from "../api/schemas"
import { Button, Input } from "@heroui/react"
import StringSelect from "./StringSelect"
import { CodeEditor } from "./CodeEditor"

export default function EditConfiguration({
	configuration,
	onSave,
}: {
	configuration: Config | null
	onSave: (config: Config) => void
}) {
	const [editedConfig, setEditedConfig] = useState(
		configuration ?? {
			config_id: "",
			config_name: "",
			config_text: "",
			updated_at: new Date().toISOString(),
			default_duration: 10,
			tracing_tool: undefined,
		}
	)

	return (
		<>
			<Input
				label="Configuration Name"
				size="lg"
				value={editedConfig.config_name}
				onChange={(e) =>
					setEditedConfig({
						...editedConfig,
						config_name: e.target.value,
					})
				}
				labelPlacement="outside"
				placeholder="Enter the configuration name..."
			/>
			<div className="h-4"></div>
			<Input
				label="Default Duration (seconds)"
				size="lg"
				type="number"
				value={`${editedConfig.default_duration}`}
				onChange={(e) =>
					setEditedConfig({
						...editedConfig,
						default_duration: Number(e.target.value),
					})
				}
				labelPlacement="outside"
			/>
			<div className="h-4"></div>
			<StringSelect
				label="Tracing Tool"
				value={editedConfig.tracing_tool || ""}
				onValueChange={(value) =>
					setEditedConfig({
						...editedConfig,
						tracing_tool: value || undefined,
					})
				}
				detailedOptions={{
					perfetto: "Perfetto",
				}}
			/>
			<div className="h-4"></div>
			<p className="mb-1 font-medium">Configuration Text (.pbtxt)</p>
			<CodeEditor
				value={editedConfig.config_text || ""}
				onValueChange={(code) =>
					setEditedConfig({
						...editedConfig,
						config_text: code,
					})
				}
			/>
			<div className="h-4"></div>
			<Button
				color="primary"
				size="md"
				onPress={() => {
					onSave(editedConfig)
				}}
			>
				Save Changes
			</Button>
		</>
	)
}
