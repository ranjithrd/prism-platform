import { useMemo } from "react"
import { useGetConfigurationsV1ApiConfigurationsGet } from "../api/api-client"
import dayjs from "dayjs"
import ConfigurationCard from "./ConfigurationCard"
import { Link } from "wouter"
import { ArrowRightIcon } from "@heroicons/react/20/solid"

export default function RecentConfigurations() {
	const { data: configurations, isLoading } =
		useGetConfigurationsV1ApiConfigurationsGet()
	const processedConfigurations = useMemo(() => {
		// sort by updated_at using dayjs
		return (
			configurations?.sort((a, b) =>
				dayjs(b.updated_at).diff(dayjs(a.updated_at))
			) || []
		)
	}, [configurations])

	if (isLoading) {
		return <div>Loading...</div>
	}

	return (
		<div className="flex flex-col gap-4">
			<Link href="/configurations">
				<h2 className="text-xl font-bold">
					Recent Configurations{" "}
					<ArrowRightIcon className="inline size-4" />
				</h2>
			</Link>
			<div className="flex flex-row flex-wrap gap-2">
				{processedConfigurations.map((config) => (
					<ConfigurationCard key={config.config_id} config={config} />
				))}
			</div>
		</div>
	)
}
