import React from "react"

export function CodeEditor({
	value,
	onValueChange,
}: {
	value: string
	onValueChange: (newValue: string) => void
}) {
	const handleChange = (event: React.ChangeEvent<HTMLTextAreaElement>) => {
		onValueChange(event.target.value)
	}

	return (
		<textarea
			value={value}
			onChange={handleChange}
			spellCheck="false"
			autoCapitalize="none"
			autoComplete="off"
			autoCorrect="off"
			// Basic styling to look like a code editor
			className="w-full h-64 p-4 font-mono text-sm border rounded-lg  border-default-300 bg-default-50 focus:outline-none focus:ring-2 focus:ring-primary-500 dark:bg-default-100 dark:border-default-200"
		/>
	)
}
