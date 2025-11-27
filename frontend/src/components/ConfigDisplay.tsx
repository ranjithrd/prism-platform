import React, { useState } from "react"
import { Button, Tooltip } from "@heroui/react"
import { ClipboardIcon, CheckIcon } from "@heroicons/react/20/solid"

interface ConfigDisplayProps {
	/** The text content to display, with \n newlines */
	text: string
	/** Optional: The tracing tool type to determine formatting */
	tracingTool?: string
}

export const ConfigDisplay: React.FC<ConfigDisplayProps> = ({
	text,
	tracingTool,
}) => {
	const [isCopied, setIsCopied] = useState(false)

	// Try to format JSON for simpleperf configs
	const displayText = React.useMemo(() => {
		if (tracingTool === "simpleperf") {
			try {
				const parsed = JSON.parse(text)
				return JSON.stringify(parsed, null, 2)
			} catch {
				return text
			}
		}
		return text
	}, [text, tracingTool])

	const handleCopy = async () => {
		if (!navigator.clipboard) {
			return
		}
		try {
			await navigator.clipboard.writeText(text)
			setIsCopied(true)
			setTimeout(() => setIsCopied(false), 2000)
		} catch (err) {
			console.error("Failed to copy text: ", err)
		}
	}

	return (
		<div className="relative p-4 border rounded-lg border-default-200 bg-default-50">
			<Tooltip
				content={isCopied ? "Copied!" : "Copy config"}
				placement="top"
			>
				<Button
					isIconOnly
					size="sm"
					variant="light"
					className="absolute right-2 top-2 text-default-500"
					onPress={handleCopy}
				>
					{isCopied ? (
						<CheckIcon className="w-5 h-5 text-green-500" />
					) : (
						<ClipboardIcon className="w-5 h-5" />
					)}
				</Button>
			</Tooltip>

			<p className="font-mono text-sm whitespace-pre-wrap wrap-break-word">
				{displayText}
			</p>
		</div>
	)
}
