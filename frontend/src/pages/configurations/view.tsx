import {
	deleteConfigurationV1ApiConfigurationsConfigIdDeletePost,
	editConfigurationV1ApiConfigurationsConfigIdEditPost,
	useGetConfigurationV1ApiConfigurationsConfigIdGet,
} from "../../api/api-client"
import { Layout } from "../../components/Layout"
import { useState } from "react"
import { InlineQueries } from "../../components/InlineQueries"
import type { Config, Query } from "../../api/schemas"
import { RecentTracesByConfig } from "../../components/RecentTraces"
import ViewEditConfiguration from "../../components/ViewEditConfiguration"
import { autoToast } from "../../components/toast"
import { useLocation } from "wouter"
import { Button } from "@heroui/react"

export function ConfigurationsViewPage({ id }: { id: string }) {
	const [showConfig, setShowConfig] = useState(false)
	const [editing, setEditing] = useState(false)
	const [, navigate] = useLocation()

	const {
		data: configuration,
		isLoading,
		mutate,
	} = useGetConfigurationV1ApiConfigurationsConfigIdGet(id)

	if (isLoading) {
		return <Layout>Loading...</Layout>
	}

	if (!configuration) {
		return <Layout>Configuration not found!</Layout>
	}

	async function onRun() {
		if (!configuration) return
		navigate(`/groupQuery?configuration_id=${configuration.config_id}`)
	}

	async function onSave(config: Config) {
		console.log("Saved configuration:", config)
		await autoToast(
			editConfigurationV1ApiConfigurationsConfigIdEditPost(id, {
				config_name: config.config_name ?? "",
				config_text: config.config_text ?? "",
				default_duration: config.default_duration ?? 10,
				tracing_tool: config.tracing_tool ?? "",
			}),
			{
				loadingText: "Saving configuration...",
				successText: "Configuration saved!",
				errorText: "Failed to save configuration.",
			}
		)
		mutate()
		setEditing(false)
	}

	async function onDelete() {
		const confirmed = window.confirm(
			"Are you sure you want to delete this configuration? This action cannot be undone."
		)
		if (!confirmed) return

		autoToast(
			deleteConfigurationV1ApiConfigurationsConfigIdDeletePost(id),
			{
				loadingText: "Deleting configuration...",
				successText: "Configuration deleted!",
				errorText: "Failed to delete configuration.",
			}
		).then(() => {
			navigate("/configurations")
		})
	}

	return (
		<Layout>
			<ViewEditConfiguration
				configuration={configuration}
				showConfig={showConfig}
				setShowConfig={setShowConfig}
				editing={editing}
				setEditing={setEditing}
				onSave={onSave}
			/>
			<div className="h-4"></div>
			<h2 className="text-xl font-bold">Recent Traces</h2>
			{configuration.config_id && (
				<RecentTracesByConfig config={configuration} />
			)}
			<div className="h-4"></div>
			<InlineQueries
				showTitle
				configId={configuration.config_id}
				onRunAnalysis={onRun}
			/>
			<div className="h-4"></div>
			<Button
				color="danger"
				variant="bordered"
				onPress={onDelete}
				className="w-min"
			>
				Delete Configuration
			</Button>
		</Layout>
	)
}
