import { Input, Chip, Switch } from "@heroui/react"
import { useState } from "react"
import StringSelect from "./StringSelect"

interface SimpleperfConfig {
	debug_app_id: string
	events: string[]
	frequency: number
	call_graph: string
	record_command: string
	extra_args: string[]
	root_mode: boolean
}

export default function SimpleperfConfigInput({
	configText,
	setConfigText,
}: {
	configText: string
	setConfigText: (text: string) => void
}) {
	const parseConfig = (text: string): SimpleperfConfig => {
		try {
			const parsed = JSON.parse(text)
			return {
				debug_app_id: parsed.debug_app_id || "",
				events: parsed.events || ["cpu-cycles"],
				frequency: parsed.frequency || 4000,
				call_graph: parsed.call_graph || "dwarf",
				record_command: parsed.record_command || "record",
				extra_args: parsed.extra_args || [],
				root_mode: parsed.root_mode || false,
			}
		} catch {
			return {
				debug_app_id: "",
				events: ["cpu-cycles"],
				frequency: 4000,
				call_graph: "dwarf",
				record_command: "record",
				extra_args: [],
				root_mode: false,
			}
		}
	}

	const [config, setConfig] = useState<SimpleperfConfig>(
		parseConfig(configText)
	)
	const [newEvent, setNewEvent] = useState("")
	const [newArg, setNewArg] = useState("")
	const [isSystemLevel, setIsSystemLevel] = useState(
		config.debug_app_id.toLowerCase() === "system"
	)

	const updateConfigText = (updatedConfig: SimpleperfConfig) => {
		setConfig(updatedConfig)
		setConfigText(JSON.stringify(updatedConfig, null, 2))
	}

	const handleProfilingLevelChange = (systemLevel: boolean) => {
		setIsSystemLevel(systemLevel)
		const updatedConfig = {
			...config,
			debug_app_id: systemLevel ? "system" : "",
			// Auto-enable root mode when switching to system-level
			root_mode: systemLevel ? true : config.root_mode,
		}
		updateConfigText(updatedConfig)
	}

	const addEvent = () => {
		if (newEvent.trim()) {
			updateConfigText({
				...config,
				events: [...config.events, newEvent.trim()],
			})
			setNewEvent("")
		}
	}

	const removeEvent = (index: number) => {
		updateConfigText({
			...config,
			events: config.events.filter((_, i) => i !== index),
		})
	}

	const addExtraArg = () => {
		if (newArg.trim()) {
			updateConfigText({
				...config,
				extra_args: [...config.extra_args, newArg.trim()],
			})
			setNewArg("")
		}
	}

	const removeExtraArg = (index: number) => {
		updateConfigText({
			...config,
			extra_args: config.extra_args.filter((_, i) => i !== index),
		})
	}

	return (
		<div className="flex flex-col gap-4">
			<Switch
				isSelected={config.root_mode}
				onValueChange={(value) => {
					// Don't allow disabling root mode if system-level is enabled
					if (isSystemLevel && !value) {
						return
					}
					updateConfigText({ ...config, root_mode: value })
				}}
			>
				<div className="flex flex-col">
					<p className="text-sm font-medium">Root Mode</p>
					<p className="text-xs text-default-500">
						Run adb root before tracing
					</p>
				</div>
			</Switch>

			<Switch
				isSelected={isSystemLevel}
				onValueChange={handleProfilingLevelChange}
				isDisabled={!config.root_mode}
			>
				<div className="flex flex-col">
					<p className="text-sm font-medium">System-Level Profiling</p>
					<p className="text-xs text-default-500">
						Profile entire system instead of a specific app.{" "}
						<span className="font-bold">Requires root mode.</span>
					</p>
				</div>
			</Switch>

			{!isSystemLevel && (
				<Input
					label="App Package Name"
					placeholder="com.example.app"
					description="Package name of the app to profile"
					value={config.debug_app_id}
					onChange={(e) =>
						updateConfigText({
							...config,
							debug_app_id: e.target.value,
						})
					}
					labelPlacement="outside"
					isRequired
				/>
			)}

			<Input
				label="Sampling Frequency (Hz)"
				type="number"
				placeholder="4000"
				description="Number of samples per second"
				value={String(config.frequency)}
				onChange={(e) =>
					updateConfigText({
						...config,
						frequency: Number(e.target.value) || 4000,
					})
				}
				labelPlacement="outside"
			/>

			<StringSelect
				label="Call Graph Method"
				value={config.call_graph}
				onValueChange={(value) =>
					updateConfigText({ ...config, call_graph: value })
				}
				detailedOptions={{
					none: "None",
					dwarf: "DWARF (Recommended)",
					fp: "Frame Pointer",
				}}
			/>

			<StringSelect
				label="Record Command"
				value={config.record_command}
				onValueChange={(value) =>
					updateConfigText({ ...config, record_command: value })
				}
				detailedOptions={{
					record: "Record",
				}}
			/>

			<div>
				<p className="mb-2 text-sm font-medium">Events to Trace</p>
				<p className="mb-2 text-xs text-default-500">
					Common events: cpu-cycles, instructions, cache-references,
					cache-misses, branch-instructions, branch-misses
				</p>
				<div className="flex flex-wrap gap-2 mb-2">
					{config.events.map((event, index) => (
						<Chip
							key={index}
							onClose={() => removeEvent(index)}
							variant="flat"
						>
							{event}
						</Chip>
					))}
				</div>
				<div className="flex gap-2">
					<Input
						placeholder="Enter event name..."
						value={newEvent}
						onChange={(e) => setNewEvent(e.target.value)}
						onKeyPress={(e) => {
							if (e.key === "Enter") {
								addEvent()
							}
						}}
						size="sm"
					/>
					<button
						type="button"
						onClick={addEvent}
						className="px-4 py-2 text-sm text-white rounded-lg bg-sky-700 hover:bg-sky-800"
					>
						Add
					</button>
				</div>
			</div>

			<div>
				<p className="mb-2 text-sm font-medium">
					Extra Arguments (Optional)
				</p>
				<div className="flex flex-wrap gap-2 mb-2">
					{config.extra_args.map((arg, index) => (
						<Chip
							key={index}
							onClose={() => removeExtraArg(index)}
							variant="flat"
						>
							{arg}
						</Chip>
					))}
				</div>
				<div className="flex gap-2">
					<Input
						placeholder="--no-inherit, --cpu 0..."
						value={newArg}
						onChange={(e) => setNewArg(e.target.value)}
						onKeyPress={(e) => {
							if (e.key === "Enter") {
								addExtraArg()
							}
						}}
						size="sm"
					/>
					<button
						type="button"
						onClick={addExtraArg}
						className="px-4 py-2 text-sm text-white rounded-lg bg-sky-700 hover:bg-sky-800"
					>
						Add
					</button>
				</div>
			</div>
		</div>
	)
}
