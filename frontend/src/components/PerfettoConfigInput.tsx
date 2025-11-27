import { CodeEditor } from "./CodeEditor"

export default function PerfettoConfigInput({
	configText,
	setConfigText,
}: {
	configText: string
	setConfigText: (text: string) => void
}) {
	return (
		<div className="flex flex-col gap-2">
			<p className="text-sm text-default-500">
				Enter your Perfetto configuration in Protocol Buffer text
				format (.pbtxt)
			</p>
			<CodeEditor value={configText} onValueChange={setConfigText} />
		</div>
	)
}
