import { ChevronDownIcon } from "@heroicons/react/20/solid"
import {
	Button,
	ButtonGroup,
	Dropdown,
	DropdownItem,
	DropdownMenu,
	DropdownTrigger,
} from "@heroui/react"
import { useState } from "react"

export default function ExportButtonGroup({
	handleExport,
}: {
	handleExport: (format: "csv" | "tsv" | "json") => void
}) {
	const [selectedOption, setSelectedOption] = useState(new Set(["csv"]))

	const labelsMap = {
		csv: "Export as CSV",
		tsv: "Export as TSV",
		json: "Export as JSON",
	}

	// Convert the Set to an Array and get the first value.
	const selectedOptionValue = Array.from(selectedOption)[0]

	return (
		<ButtonGroup color="primary" className="w-min">
			<Button
				onPress={() => {
					handleExport(selectedOptionValue as "csv" | "tsv" | "json")
				}}
			>
				{labelsMap[selectedOptionValue as "csv" | "tsv" | "json"]}
			</Button>
			<Dropdown placement="bottom-end">
				<DropdownTrigger>
					<Button isIconOnly>
						<ChevronDownIcon className="size-6" />
					</Button>
				</DropdownTrigger>
				<DropdownMenu
					disallowEmptySelection
					aria-label="Export options"
					className="max-w-[300px]"
					selectedKeys={selectedOption}
					selectionMode="single"
					// @ts-expect-error: setSelectedOption expects Set<string>
					onSelectionChange={setSelectedOption}
				>
					<DropdownItem
						key="csv"
					>
						{labelsMap["csv"]}
					</DropdownItem>
					<DropdownItem
						key="tsv"
					>
						{labelsMap["tsv"]}
					</DropdownItem>
					<DropdownItem
						key="json"
					>
						{labelsMap["json"]}
					</DropdownItem>
				</DropdownMenu>
			</Dropdown>
		</ButtonGroup>
	)
}
