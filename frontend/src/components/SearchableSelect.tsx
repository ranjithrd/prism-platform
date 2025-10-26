import {
	Button,
	Checkbox,
	Input,
	Modal,
	ModalBody,
	ModalContent,
	ModalFooter,
	ModalHeader,
	useDisclosure,
} from "@heroui/react"
import { useEffect, useState } from "react"

export default function SearchableSelect({
	getOptions,
	value,
	setValue,
	label,
	minCharacters,
	multiselect,
	disabled,
	cta,
	ctaLabel,
	customDisplay,
	chooseFirst,
}:
	| {
			getOptions: (
				query: string
			) => Promise<{ [key: string]: number | string }>
			value: number | string | null
			setValue: (newValue: string | null) => void
			label: string
			minCharacters?: number
			multiselect?: false
			disabled?: boolean
			cta?: () => {}
			ctaLabel?: string
			customDisplay?: null | undefined
			chooseFirst?: boolean
	  }
	| {
			getOptions: (
				query: string
			) => Promise<{ [key: string]: number | string }>
			value: number[] | string[]
			setValue: (newValue: string[]) => void
			label: string
			minCharacters?: number
			multiselect: true
			disabled?: boolean
			cta?: (value: string[], onClose: Function) => void
			ctaLabel?: string
			customDisplay?: (onOpen: Function) => React.ReactNode
			chooseFirst?: boolean
	  }) {
	const [query, setQuery] = useState<string>("")
	const [selected, setSelected] = useState<string | null>("")
	const { isOpen, onOpen, onOpenChange } = useDisclosure()
	const [options, setOptions] = useState<{ [key: string]: number | string }>(
		{}
	)

	async function updateOptions() {
		const options = await getOptions(query)

		setOptions(options)

		if (value) {
			if (multiselect) {
				setSelected(`${(value as string[]).length} selected`)
			} else {
				setSelected(
					Object.keys(options).includes(`${value}`)
						? `${options[value as string | number] ?? null}`
						: null
				)
			}
		}
	}

	useEffect(() => {
		const handler = setTimeout(() => {
			if (query && value && minCharacters && query.length < minCharacters)
				return

			updateOptions()
		}, 500)

		return () => clearTimeout(handler) // Cleanup timeout on dependency change
	}, [query, value])

	useEffect(() => {
		updateOptions()
	}, [])

	function multiselectSelected(k: string | number) {
		return ((value ?? []) as number[] | string[])
			.map((e) => `${e}`)
			.includes(`${k}`)
	}

	function multiselectToggle(k: string | number) {
		if (multiselect) {
			if (value.map((e) => `${e}`).includes(`${k}`)) {
				setValue(value.map((e) => `${e}`).filter((e) => e !== `${k}`))
			} else {
				setValue([...value.map((x) => `${x}`), `${k}`])
			}
		}
	}

	function multiselectToggleAll() {
		if (multiselect) {
			if (value.length == 0) {
				setValue(Object.keys(options))
			} else {
				setValue([])
			}
		}
	}

	useEffect(() => {
		if (!multiselect && chooseFirst && Object.keys(options).length === 1) {
			const firstKey = Object.keys(options)[0]

			if (firstKey) {
				// @ts-expect-error inference cannot figure out multiselect = false => value is string
				setValue(firstKey)
				setSelected(`${options[firstKey]}`)
			}
		}
	}, [options])

	return (
		<>
			{multiselect && customDisplay ? (
				customDisplay(onOpen)
			) : (
				<div className="flex flex-col w-full gap-2 p-2">
					<div className="text-sm font-bold">{label}</div>
					<Button
						className="w-full"
						isDisabled={disabled}
						variant="ghost"
						onPress={
							disabled
								? () => {}
								: () => {
										updateOptions()
										onOpen()
								  }
						}
					>
						{selected ? selected : "Click to select"}
					</Button>
				</div>
			)}
			<Modal
				className="z-100"
				classNames={{
					backdrop: "z-100",
					base: "z-120",
					body: "z-130",
					wrapper: "z-130",
				}}
				isOpen={isOpen}
				onOpenChange={onOpenChange}
			>
				<ModalContent>
					{(onClose) => (
						<>
							<ModalHeader>{label}</ModalHeader>
							<ModalBody className="h-64 p-6 pt-0 overflow-y-auto">
								<Input
									aria-label="Search..."
									placeholder="Search..."
									value={query}
									onValueChange={setQuery}
								/>
								{multiselect ? (
									<div className="flex flex-row w-full gap-2">
										<Checkbox
											isIndeterminate={
												value.length > 0 &&
												value.length <
													Object.keys(options).length
											}
											isSelected={
												value.length ==
												Object.keys(options).length
											}
											onValueChange={multiselectToggleAll}
										/>
										<button
											className="flex flex-row w-full gap-2 p-2 underline"
											onClick={multiselectToggleAll}
										>
											<p>All</p>
										</button>
									</div>
								) : (
									<></>
								)}
								{Object.entries(options).map(([k, v]) => (
									<div
										key={k}
										className="flex flex-row w-full gap-2"
									>
										{multiselect ? (
											<Checkbox
												isSelected={multiselectSelected(
													k
												)}
												onValueChange={() => {
													multiselectToggle(k)
												}}
											/>
										) : (
											<></>
										)}
										<button
											className="flex flex-row w-full gap-2 p-2 underline"
											onClick={() => {
												if (multiselect === true) {
													multiselectToggle(k)
												} else {
													setValue(k)
													onClose()
												}
											}}
										>
											<p>{v}</p>
										</button>
									</div>
								))}
								{Object.values(options).length == 0 ? (
									<p>No records found</p>
								) : (
									<></>
								)}
							</ModalBody>
							{multiselect ? (
								cta ? (
									<ModalFooter>
										<Button
											color="primary"
											onPress={() =>
												cta(
													value.map((e) => `${e}`),
													onClose
												)
											}
										>
											{ctaLabel ?? ""}
										</Button>
									</ModalFooter>
								) : (
									<ModalFooter>
										<Button
											color="primary"
											onPress={() => {
												onClose()
												setQuery("")
											}}
										>
											Done
										</Button>
									</ModalFooter>
								)
							) : (
								<></>
							)}
						</>
					)}
				</ModalContent>
			</Modal>
		</>
	)
}
