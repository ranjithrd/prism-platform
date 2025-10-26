import { useMemo, useState } from "react"
import {
	createQueryV1ApiQueriesPost,
	deleteQueryV1ApiQueriesQueryIdDeletePost,
	editQueryV1ApiQueriesQueryIdEditPost,
	useGetConfigurationsV1ApiConfigurationsGet,
	useGetQueriesV1ApiQueriesGet,
} from "../api/api-client"
import type { Config, Query } from "../api/schemas"
import {
	Button,
	Card,
	CardBody,
	CardFooter,
	Checkbox,
	Input,
	Modal,
	ModalBody,
	ModalContent,
	ModalHeader,
	useDisclosure,
} from "@heroui/react"
import {
	ArrowPathIcon,
	PencilIcon,
	PlayIcon,
	PlusIcon,
	TrashIcon,
} from "@heroicons/react/20/solid"
import CodeView from "./CodeView"
import { autoToast, autoToastError } from "./toast"
import ResponsiveGrid from "./ResponsiveGrid"
import Fuse from "fuse.js"
import EditQuery from "./EditQuery"

export function InlineAddQueryCard({
	configId,
	refetch,
}: {
	configId?: string | null
	refetch: () => void
}) {
	const { isOpen, onOpen, onClose } = useDisclosure()

	function handleCreate(onClose: () => void) {
		return async (query: Query) => {
			if (!query.query_name || !query.query_text) {
				autoToastError("Query name and text are required.", null)
				return
			}

			await autoToast(
				createQueryV1ApiQueriesPost({
					query_name: query.query_name!,
					query_text: query.query_text!,
					configuration_id: query.configuration_id,
				}),
				{
					loadingText: "Creating Query...",
					successText: "Query created successfully!",
					errorText: "Failed to create query.",
				}
			)
			await refetch()
			onClose()
		}
	}

	return (
		<Card className="p-4" onClick={onOpen} isPressable>
			<CardBody className="flex justify-end w-full p-4 cursor-pointer">
				<h3 className="text-xl font-semibold">
					<PlusIcon className="inline size-4" /> Add a Query
				</h3>
			</CardBody>
			<Modal isOpen={isOpen} onClose={onClose}>
				<ModalContent>
					{(onClose) => (
						<>
							<ModalHeader>
								<h3 className="text-lg font-semibold">
									New Query
								</h3>
							</ModalHeader>
							<ModalBody className="flex flex-col mb-4">
								<EditQuery
									query={{
										query_name: "",
										query_text: "",
										configuration_id: configId || undefined,
									}}
									onSave={handleCreate(onClose)}
								/>
							</ModalBody>
						</>
					)}
				</ModalContent>
			</Modal>
		</Card>
	)
}

export function InlineQueryCard({
	query,
	onRun,
	refetch = () => {},
	configurations,
}: {
	query: Query
	onRun?: (query: Query) => void
	refetch?: () => void
	configurations?: Config[]
}) {
	const { isOpen, onOpen, onClose } = useDisclosure()

	const chosenConfigurationName = useMemo<string | null>(() => {
		return (
			configurations?.find(
				(config) => config.config_id === query.configuration_id
			)?.config_name ?? null
		)
	}, [configurations, query])

	function handleSave(onClose: () => void) {
		return async (query: Query) => {
			if (!query.query_name || !query.query_text) {
				autoToastError("Query name and text are required.", null)
				return
			}

			await autoToast(
				editQueryV1ApiQueriesQueryIdEditPost(query.query_id || "", {
					query_name: query.query_name!,
					query_text: query.query_text!,
					configuration_id: query.configuration_id,
				}),
				{}
			)
			await refetch()
			onClose()
		}
	}

	async function handleDelete() {
		await autoToast(
			deleteQueryV1ApiQueriesQueryIdDeletePost(query.query_id || ""),
			{}
		)
		refetch()
	}

	return (
		<Card className="w-full p-2">
			<CardBody className="flex flex-col gap-2">
				<h3 className="text-lg font-semibold">{query.query_name}</h3>
				{chosenConfigurationName && (
					<p className="text-sm">
						Configuration: {chosenConfigurationName}
					</p>
				)}
				<CodeView fullText={query.query_text || ""}>
					{query.query_text ?? ""}
				</CodeView>
			</CardBody>
			<CardFooter className="flex flex-row justify-between w-full gap-2">
				<div className="flex flex-row gap-2">
					<Button
						isIconOnly
						color="danger"
						variant="bordered"
						size="sm"
						aria-label="Delete Query"
						onPress={handleDelete}
					>
						<TrashIcon className="size-4" />
					</Button>
					<Button
						isIconOnly
						color="warning"
						variant="bordered"
						size="sm"
						aria-label="Edit Query"
						onPress={() => onOpen()}
					>
						<PencilIcon className="size-4" />
					</Button>
				</div>
				{onRun && (
					<Button
						color="primary"
						size="sm"
						aria-label="Run Query"
						onPress={() => onRun(query)}
					>
						Run
						<PlayIcon className="size-4" />
					</Button>
				)}
			</CardFooter>
			<Modal isOpen={isOpen} onClose={onClose}>
				<ModalContent>
					{(onClose) => (
						<>
							<ModalHeader>
								<h3 className="text-lg font-semibold">
									Edit Query
								</h3>
							</ModalHeader>
							<ModalBody className="flex flex-col mb-4">
								<EditQuery
									query={query}
									onSave={handleSave(onClose)}
								/>
							</ModalBody>
						</>
					)}
				</ModalContent>
			</Modal>
		</Card>
	)
}

export function InlineQueries({
	showTitle = false,
	configId,
	onRun,
	onRunAnalysis,
	limit = 5,
}: {
	showTitle?: boolean
	configId?: string | null
	onRun?: (query: Query) => void
	onRunAnalysis?: () => void
	limit?: number
}) {
	const {
		data: allQueries,
		isLoading,
		mutate,
	} = useGetQueriesV1ApiQueriesGet()
	const { data: configurations } =
		useGetConfigurationsV1ApiConfigurationsGet()
	const [searchTerm, setSearchTerm] = useState("")
	const [limitResults, setLimitResults] = useState(true)
	const [showConfigFilter, setShowConfigFilter] = useState(true)

	const queriesToSearch = useMemo(() => {
		if (!allQueries) return []

		let queries = allQueries

		if (configId && showConfigFilter) {
			queries = queries.filter(
				(query) => query.configuration_id === configId
			)
		}

		return queries
	}, [allQueries, configId, showConfigFilter])

	const fuse = useMemo(
		() =>
			new Fuse(queriesToSearch, {
				keys: [
					{
						name: "query_name",
						weight: 0.66,
					},
					{
						name: "query_text",
						weight: 0.33,
					},
				],
				threshold: 0.4,
				ignoreLocation: true,
			}),
		[queriesToSearch]
	)

	const searchedQueries = useMemo(() => {
		if (searchTerm.trim() === "") {
			return queriesToSearch
		}

		console.log(queriesToSearch)

		const results = fuse.search(searchTerm)
		return results.map((result) => result.item)
	}, [queriesToSearch, fuse, searchTerm])

	const limitedQueries = useMemo(() => {
		if (limitResults) {
			return searchedQueries.slice(0, limit)
		}
		return searchedQueries
	}, [limitResults, searchedQueries])

	if (isLoading) {
		return <div>Loading...</div>
	}

	return (
		<>
			{showTitle && (
				<div className="flex flex-col gap-2 mb-4 md:flex-row md:justify-between md:items-center">
					<h2 className="text-2xl font-bold">Queries</h2>
					<div className="flex flex-col items-start gap-2 md:items-end">
						{onRunAnalysis && (
							<Button
								color="primary"
								className="w-min"
								onPress={() => onRunAnalysis?.()}
							>
								Run Analysis
							</Button>
						)}
						{configId && (
							<Checkbox
								isSelected={showConfigFilter}
								onValueChange={setShowConfigFilter}
								classNames={{
									base: "flex-row-reverse gap-2 items-center",
								}}
							>
								Filter for this Configuration
							</Checkbox>
						)}
					</div>
				</div>
			)}
			<div className="flex w-full gap-2">
				<Input
					placeholder="Search queries..."
					value={searchTerm}
					onValueChange={setSearchTerm}
				/>
				<Button variant="bordered" onPress={() => mutate()} isIconOnly>
					<ArrowPathIcon className="size-4" />
				</Button>
			</div>
			<div className="h-4"></div>
			{limitedQueries.length === 0 && (
				<>
					<p className="text-gray-600">No queries found!</p>
					<div className="h-4"></div>
				</>
			)}
			<ResponsiveGrid>
				{limitedQueries.map((query) => (
					<InlineQueryCard
						key={query.query_id ?? ""}
						query={query}
						onRun={onRun}
						refetch={() => mutate()}
						configurations={configurations ?? []}
					/>
				))}
				<InlineAddQueryCard
					configId={configId}
					refetch={() => mutate()}
				/>
			</ResponsiveGrid>
			{searchedQueries.length > limit && (
				<div className="flex justify-center mt-4">
					<Button
						variant="light"
						size="sm"
						onPress={() => setLimitResults(!limitResults)}
					>
						{limitResults ? "Show All" : "Show Less"}
					</Button>
				</div>
			)}
		</>
	)
}
