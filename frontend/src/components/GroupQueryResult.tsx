import { DataGrid } from "@mui/x-data-grid"
import { useMemo } from "react"
import { useGetJsonResultV1ApiGroupResultsQueryIdJsonGet } from "../api/api-client"
import type { Query } from "../api/schemas"
import ExportButtonGroup from "./ExportButtonGroup"
import { ConfigDisplay } from "./ConfigDisplay"
import { AXIOS_INSTANCE } from "../api/axios"

export function GroupQueryResultTable({
	queryId,
	traceIds,
}: {
	queryId: string
	traceIds: string
}) {
	const { data: queryResultData, isLoading } =
		useGetJsonResultV1ApiGroupResultsQueryIdJsonGet(queryId, {
			trace_ids: traceIds,
		}, {
			swr: {
				revalidateOnFocus: false,
				revalidateIfStale: false,
			},
		})

	const columns = useMemo(() => {
		// @ts-expect-error: columns type inference
		const columnNames = (queryResultData?.columns as string[]) ?? []
		return columnNames.map((colName: string) => ({
			field: colName,
			headerName: colName,
			width: 150,
		}))
	}, [queryResultData])

	const rows = useMemo(() => {
		return (
			// @ts-expect-error: data type inference
			(queryResultData?.data as object[])?.map(
				(row: unknown, index: number) => ({
					id: index,
					// @ts-expect-error: row type inference
					...row,
				})
			) ?? []
		)
	}, [queryResultData])

	if (isLoading) {
		return <div>Loading...</div>
	}

	return (
		<div className="h-[80vh]">
			<DataGrid
				rows={rows}
				columns={columns}
				style={{
					fontFamily: "Hanken Grotesk",
				}}
			/>
		</div>
	)
}

export function GroupQueryResult({
	query,
	traceIds,
}: {
	query: Query
	traceIds: string
}) {
	async function handleExport(format: "csv" | "tsv" | "json") {
		const response = await fetch(
			`${AXIOS_INSTANCE.defaults.baseURL}/v1/api/group_results/${query.query_id}/export?file_format=${format}&trace_ids=${traceIds}`,
		)
		if (!response.ok) {
			alert("Failed to export data")
			return
		}
		const blob = await response.blob()
		const url = window.URL.createObjectURL(blob)
		const a = document.createElement("a")
		a.href = url
		a.download = `${query.query_name || "query_result"} ${traceIds}.${format}`
		document.body.appendChild(a)
		a.click()
		a.remove()
		window.URL.revokeObjectURL(url)
	}

	return (
		<>
			<div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
				<h2 className="text-xl font-bold">{query.query_name}</h2>
				<ExportButtonGroup handleExport={handleExport} />
			</div>
			<div className="h-2"></div>
			<ConfigDisplay text={query.query_text ?? ""} />
			<div className="h-4"></div>
			<GroupQueryResultTable
				queryId={query.query_id ?? ""}
				traceIds={traceIds}
			/>
		</>
	)
}
