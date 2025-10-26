import { useLocation, useSearchParams } from "wouter"
import { Layout } from "../components/Layout"
import {
	createJobRequestV1ApiRequestsPost,
	useGetConfigurationsV1ApiConfigurationsGet,
	useGetDevicesV1ApiDevicesGet,
} from "../api/api-client"
import { useEffect, useMemo, useRef, useState } from "react"
import ChooseConfigCard from "../components/ChooseConfigCard"
import ResponsiveGrid from "../components/ResponsiveGrid"
import ChooseDeviceCard from "../components/ChooseDeviceCard"
import { Button, Input } from "@heroui/react"
import { ArrowRightIcon } from "@heroicons/react/20/solid"
import { autoToast, autoToastError } from "../components/toast"

export default function StartTracePage() {
	const [searchParams, setSearchParams] = useSearchParams()
	const configuration_id = searchParams.get("configuration_id") || ""
	const device_ids = searchParams.get("device_ids") || ""
	const url_duration = parseInt(searchParams.get("duration") ?? "") || 10

	const [, setLocation] = useLocation()

	const { data: allConfigurations, isLoading: configsLoading } =
		useGetConfigurationsV1ApiConfigurationsGet()
	const { data: allDevices, isLoading: devicesLoading } =
		useGetDevicesV1ApiDevicesGet({
			swr: {
				refreshInterval: 10_000,
			},
		})

	const [chosenConfigurationId, setChosenConfigurationId] = useState<
		string | null
	>(configuration_id || null)
	const [chosenDevices, setChosenDevices] = useState<string[]>([])
	const [duration, setDuration] = useState<string>(url_duration.toString())

	const parsedDeviceIds = useMemo(
		() => (device_ids ? device_ids.split(",").map((id) => id.trim()) : []),
		[device_ids]
	)

	const chosenConfigurationData = useMemo(() => {
		return allConfigurations?.find(
			(config) => config.config_id === chosenConfigurationId
		)
	}, [allConfigurations, chosenConfigurationId])

	const manuallySetDuration = useRef(false)

	async function startTrace() {
		if (!chosenConfigurationId) {
			autoToastError("Please select a configuration", null)
			return
		}
		if (chosenDevices.length === 0) {
			autoToastError("No devices selected", null)
			return
		}
		if (parseInt(duration) <= 0) {
			autoToastError("Duration must be greater than 0", null)
			return
		}

		const result = await autoToast(
			createJobRequestV1ApiRequestsPost({
				config_id: chosenConfigurationId!,
				devices: chosenDevices,
				duration: parseInt(duration),
			}),
			{
				loadingText: "Starting trace...",
				successText: "Trace started successfully!",
				errorText: "Failed to start trace.",
			}
		)

		if (result && result.job_id) {
			setLocation(`/job/${result.job_id}`)
		}
	}

	useEffect(() => {
		if (
			!manuallySetDuration.current &&
			chosenConfigurationData?.default_duration
		) {
			setDuration(chosenConfigurationData.default_duration.toString())
		}
	}, [chosenConfigurationData])

	useEffect(() => {
		if (
			allConfigurations &&
			allConfigurations.length > 0 &&
			configuration_id
		) {
			if (
				allConfigurations.find(
					(config) => config.config_id === configuration_id
				)
			) {
				setChosenConfigurationId(configuration_id)
			}
		}
	}, [configuration_id, allConfigurations])

	useEffect(() => {
		if (allDevices && allDevices.length > 0 && parsedDeviceIds.length > 0) {
			const validDeviceIds = allDevices
				.filter((device) => parsedDeviceIds.includes(device.device_id!))
				.map((device) => device.device_id!)
			setChosenDevices(validDeviceIds)
		}
	}, [parsedDeviceIds, allDevices])

	useEffect(() => {
		if (
			chosenConfigurationId &&
			chosenConfigurationId !== configuration_id
		) {
			searchParams.set("configuration_id", chosenConfigurationId)
			setSearchParams(searchParams)
		} else if (!chosenConfigurationId && configuration_id) {
			searchParams.delete("configuration_id")
			setSearchParams(searchParams)
		}
		if (chosenDevices.length > 0) {
			const deviceIdsStr = chosenDevices.join(",")
			if (deviceIdsStr !== device_ids) {
				searchParams.set("device_ids", deviceIdsStr)
				setSearchParams(searchParams)
			}
		} else if (device_ids) {
			searchParams.delete("device_ids")
			setSearchParams(searchParams)
		}
		if (duration && parseInt(duration) > 0) {
			if (duration !== url_duration.toString()) {
				searchParams.set("duration", duration)
				setSearchParams(searchParams)
			}
		} else if (url_duration) {
			searchParams.delete("duration")
			setSearchParams(searchParams)
		}
		// eslint-disable-next-line react-hooks/exhaustive-deps
	}, [chosenConfigurationId, chosenDevices, duration])

	if (configsLoading || devicesLoading) {
		return <Layout>Loading...</Layout>
	}

	return (
		<Layout>
			<h1 className="text-3xl font-bold">Start a Trace</h1>
			<div className="h-4"></div>
			<h2 className="text-xl font-bold">Set a Duration</h2>
			<div className="h-2"></div>
			<Input
				type="number"
				value={duration}
				onChange={(e) => {
					if (!manuallySetDuration.current)
						manuallySetDuration.current = true
					setDuration(e.target.value)
				}}
				min={1}
				max={1000_000}
				step={1}
				className="max-w-xs"
				endContent={<span className="pr-2">seconds</span>}
			/>
			<div className="h-4"></div>
			<h2 className="text-xl font-bold">Choose a Configuration</h2>
			<div className="h-2"></div>
			<ResponsiveGrid>
				{(allConfigurations ?? []).map((config) => (
					<ChooseConfigCard
						config={config}
						key={config.config_id ?? ""}
						isChosen={chosenConfigurationId === config.config_id!}
						setIsChosen={(isChosen) => {
							if (isChosen) {
								setChosenConfigurationId(config.config_id ?? "")
							} else {
								setChosenConfigurationId(null)
							}
						}}
					/>
				))}
			</ResponsiveGrid>
			<div className="h-4"></div>
			<h2 className="text-xl font-bold">Choose Devices</h2>
			<div className="h-2"></div>
			<ResponsiveGrid>
				{(allDevices ?? []).map((device) => (
					<ChooseDeviceCard
						device={device}
						key={device.device_id ?? ""}
						isChosen={chosenDevices.includes(device.device_id!)}
						setIsChosen={(isChosen) => {
							if (isChosen) {
								setChosenDevices([
									...chosenDevices,
									device.device_id ?? "",
								])
							} else {
								setChosenDevices(
									chosenDevices.filter(
										(id) => id !== device.device_id
									)
								)
							}
						}}
					/>
				))}
			</ResponsiveGrid>
			<div className="h-24"></div>
			<div className="fixed bottom-0 left-0 right-0 flex justify-end w-full p-6 px-8 pb-8 border-t border-gray-100 bg-white/5 backdrop-blur-md">
				<Button color="primary" size="md" onPress={startTrace}>
					Start Trace <ArrowRightIcon className="size-4" />
				</Button>
			</div>
		</Layout>
	)
}
