import { useState } from "react"
import {
	createConfigurationV1ApiConfigurationsPost,
	useGetConfigurationsV1ApiConfigurationsGet,
} from "../../api/api-client"
import ConfigurationCard from "../../components/ConfigurationCard"
import { Layout } from "../../components/Layout"
import { Button } from "@heroui/react"
import EditConfiguration from "../../components/EditConfiguration"
import type { Config } from "../../api/schemas"
import { autoToast, autoToastError } from "../../components/toast"

export default function AllConfigurationsPage() {
	const [adding, setAdding] = useState(false)
	const {
		data: configurations,
		isLoading,
		mutate,
	} = useGetConfigurationsV1ApiConfigurationsGet()

	async function handleSave(config: Config) {
		const isDataValid =
			config &&
			config.config_name?.trim() !== "" &&
			config.tracing_tool?.trim() !== "" &&
			config.config_text?.trim() !== "" &&
			(config.default_duration ?? 0) > 0
		if (!isDataValid) {
			autoToastError("Please fill in all fields.", null)
            return
		}

		await autoToast(
			createConfigurationV1ApiConfigurationsPost({
				config_name: config.config_name!,
				tracing_tool: config.tracing_tool!,
				config_text: config.config_text!,
				default_duration: config.default_duration!,
			}),
			{
				loadingText: "Creating configuration...",
				successText: "Configuration created successfully!",
				errorText: "Failed to create configuration.",
			}
		)
		await mutate()
		setAdding(false)
	}

	return (
		<Layout>
			<div className="flex flex-col gap-4 md:flex-row md:justify-between md:items-center">
				<h1 className="text-2xl font-bold">Configurations</h1>
				{!adding && (
					<Button color="primary" onPress={() => setAdding(!adding)}>
						Add Configuration
					</Button>
				)}
			</div>
			{adding ? (
				<>
					<div className="h-4"></div>
					<h2 className="text-xl font-bold">Add Configuration</h2>
					<div className="h-2"></div>
					<EditConfiguration
						configuration={null}
						onSave={handleSave}
					/>
					<div className="h-2"></div>
					<Button variant="bordered" onPress={() => setAdding(false)}>
						Cancel
					</Button>
				</>
			) : null}
			<div className="h-4"></div>
			{isLoading && <p>Loading configurations...</p>}
			{!isLoading && configurations?.length === 0 && (
				<p>No configurations found.</p>
			)}
			<div className="flex flex-col gap-4">
				{configurations &&
					configurations.length > 0 &&
					configurations.map((config) => (
						<ConfigurationCard
							key={config.config_id}
							config={config}
						/>
					))}
			</div>
		</Layout>
	)
}
