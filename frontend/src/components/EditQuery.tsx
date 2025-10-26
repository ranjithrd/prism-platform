import { Button, Input } from "@heroui/react"
import type { Query } from "../api/schemas"
import { useMemo, useState } from "react"
import { CodeEditor } from "./CodeEditor"
import { useGetConfigurationsV1ApiConfigurationsGet } from "../api/api-client"
import StringSelect from "./StringSelect"

export default function EditQuery({
	query,
	onSave,
}: {
	query: Query
	onSave: (updatedQuery: Query) => void
}) {
	const [queryName, setQueryName] = useState(query.query_name || "")
	const [queryText, setQueryText] = useState(query.query_text || "")
	const [configurationId, setConfigurationId] = useState<string | undefined>(
		query.configuration_id || undefined
	)

	const { data: configurations } =
		useGetConfigurationsV1ApiConfigurationsGet()

	const chosenConfigurationName = useMemo<string | null>(() => {
		return (
			configurations?.find(
				(config) => config.config_id === configurationId
			)?.config_name ?? null
		)
	}, [configurations, configurationId])

	const configurationDetailedOptions = useMemo(() => {
		return Object.fromEntries(
			configurations?.map((config) => [
				config.config_id || "",
				config.config_name ?? config.config_id ?? "",
			]) || []
		)
	}, [configurations])

	async function handleSave() {
		onSave({
			query_id: query.query_id,
			query_name: queryName,
			query_text: queryText,
			configuration_id: configurationId,
		})
	}

	return (
		<>
			<Input
				placeholder="Enter query name..."
				label="Query Name"
                size="lg"
				labelPlacement="outside"
				value={queryName}
				onValueChange={setQueryName}
			/>
			<div className="h-2"></div>
			<StringSelect
				label="Configuration"
				value={configurationId || ""}
				onValueChange={(val) =>
					setConfigurationId(val === "" ? undefined : val)
				}
				detailedOptions={configurationDetailedOptions}
			/>
			<p className="mt-2 font-medium">Query Text (SQL)</p>
			<CodeEditor value={queryText} onValueChange={setQueryText} />
			{/* {chosenConfigurationName && (
				<p className="mt-2">
					<b>Adding to Configuration: </b>
					{chosenConfigurationName}
				</p>
			)} */}
			<Button color="primary" className="mt-2" onPress={handleSave}>
				Save Query
			</Button>
		</>
	)
}
