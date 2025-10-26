"use client"

import { Select, SelectItem } from "@heroui/react"

export default function StringSelect({
	options,
	detailedOptions,
	label,
	value,
	onValueChange,
	className,
	isRequired,
	small,
	isDisabled,
	rightAligned,
}: {
	options?: string[]
	detailedOptions?: { [key: string]: string }
	label: string
	value: string | null
	onValueChange: (newValue: string) => void
	className?: string
	isRequired?: boolean
	small?: boolean
	isDisabled?: boolean
	rightAligned?: boolean
}) {
	if (!detailedOptions && options) {
		detailedOptions = Object.fromEntries(options.map((e) => [e, e]))
	}

	return (
		<Select
			className={"w-full " + (className ?? "")}
			classNames={{
				label: rightAligned
					? "text-red-500 text-right pr-2 w-full"
					: "",
			}}
			isDisabled={isDisabled ?? false}
			isRequired={isRequired ?? false}
			label={label}
			labelPlacement="outside"
			placeholder="Click to select..."
			radius="sm"
			selectedKeys={value ? [value] : []}
			size={!small ? "lg" : "md"}
			onChange={(e) => onValueChange(e.target.value)}
		>
			{Object.entries(detailedOptions ?? {}).map(([key, value]) => (
				<SelectItem key={key} textValue={value}>
					{value}
				</SelectItem>
			))}
		</Select>
	)
}
