import React, { useState } from "react"
import { Button, Tooltip } from "@heroui/react"
import { ClipboardIcon, CheckIcon } from "@heroicons/react/20/solid"
import CodeView from "./CodeView"

interface ConfigDisplayProps {
	/** The text content to display, with \n newlines */
	text: string
}

export const ConfigDisplay: React.FC<ConfigDisplayProps> = ({ text }) => {
	const [isCopied, setIsCopied] = useState(false)

	const handleCopy = async () => {
		if (!navigator.clipboard) {
			// Clipboard API not available
			return
		}
		try {
			await navigator.clipboard.writeText(text)
			setIsCopied(true)
			setTimeout(() => setIsCopied(false), 2000) // Reset icon after 2s
		} catch (err) {
			console.error("Failed to copy text: ", err)
		}
	}

	return (
		// Use `relative` to position the copy button
		<div className="relative p-4 border rounded-lg border-default-200 bg-default-50">
			{/* Copy Button */}
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
				{text}
			</p>
		</div>
	)
}
