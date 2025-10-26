"use client"

import {
    getKeyValue,
    Link,
    Table,
    TableBody,
    TableCell,
    TableColumn,
    TableHeader,
    TableRow,
    type SortDescriptor,
} from "@heroui/react"
import { useEffect, useState } from "react"

export interface Column<T = any> {
    key: string
    label: string
    className?: (item: T) => string
    onPress?: (item: T) => any
    renderHref?: (item: T) => string
    render?: (item: T) => string | number | undefined | null
    nullValue?: string
}

export default function TableWrapper({
    columns,
    data,
    keyMethod,
    allowSorting,
    updateSortedData,
}: {
    columns: Column[]
    data: unknown[]
    keyMethod: (item: any) => string | number
    allowSorting?: boolean
    updateSortedData?: (sortedData: unknown[]) => void
}) {
    const [sortKey, setSortKey] = useState<string | null>(null)
    const [sortDirection, setSortDirection] = useState<
        "ascending" | "descending"
    >("ascending")

    const [sortedData, setSortedData] = useState([...data])

    const handleSort = (sortDescriptor: SortDescriptor) => {
        setSortKey(sortDescriptor.column.toString())
        setSortDirection(sortDescriptor.direction)

        const sorted = sortData()

        setSortedData(sorted)
        if (updateSortedData) {
            updateSortedData(sorted)
        }
    }

    const sortData = () => {
        return [...data].sort((a: any, b: any) => {
            if (!sortKey) return 0 // No sorting if no sort key is selected

            const column = columns.find((col) => col.key === sortKey)

            if (!column) return 0

            const aValue = column.render ? column.render(a) : a[sortKey]
            const bValue = column.render ? column.render(b) : b[sortKey]

            if (aValue == null || bValue == null) return 0 // Handle null/undefined values

            if (typeof aValue === "string" && typeof bValue === "string") {
                return sortDirection === "ascending"
                    ? aValue.localeCompare(bValue)
                    : bValue.localeCompare(aValue)
            }

            if (typeof aValue === "number" && typeof bValue === "number") {
                return sortDirection === "ascending"
                    ? aValue - bValue
                    : bValue - aValue
            }

            return 0
        })
    }

    const cleanedUpData = sortedData.map((item) => {
        //@ts-expect-error: data type inference
        let x = { ...item }

        for (const c of columns) {
            let val = undefined

            if (c.render) {
                val = c.render(item)
            } else {
                val = item[c.key]

                if ((val === null || val === undefined || val?.length === 0) && c.nullValue) {
                    val = c.nullValue
                }
            }

            x[c.key] = val
        }

        return x
    })

    const getColumnFromKey = (key: string) =>
        columns.filter((col) => col.key === key)[0]

    useEffect(() => {
        setSortedData(data)
    }, [data])

    return (
        <Table
            sortDescriptor={{
                column: sortKey,
                direction: sortDirection,
            }}
            onSortChange={handleSort}
        >
            <TableHeader columns={columns}>
                {(column) => (
                    <TableColumn
                        key={column.key}
                        allowsSorting={allowSorting}
                        aria-label={column.key}
                    >
                        {column.label}
                    </TableColumn>
                )}
            </TableHeader>
            <TableBody items={cleanedUpData}>
                {(item) => (
                    <TableRow key={keyMethod(item)}>
                        {(columnKey) => {
                            const col = getColumnFromKey(columnKey.toString())
                            const className = (
                                col.className ?? ((_: unknown) => "")
                            )(item)

                            if (col.onPress) {
                                return (
                                    <TableCell>
                                        <button
                                            className={`whitespace-nowrap text-primary underline ${className}`}
                                            onClick={() => col.onPress!(item)}
                                        >
                                            {getKeyValue(item, columnKey)}
                                        </button>
                                    </TableCell>
                                )
                            }

                            if (col.renderHref) {
                                return (
                                    <TableCell className="whitespace-nowrap">
                                        <Link
                                            className={`text-primary underline ${className}`}
                                            href={col.renderHref(item)}
                                        >
                                            {getKeyValue(item, columnKey)}
                                        </Link>
                                    </TableCell>
                                )
                            }

                            return (
                                <TableCell
                                    className={`${className} whitespace-nowrap`}
                                >
                                    {getKeyValue(item, columnKey)}
                                </TableCell>
                            )
                        }}
                    </TableRow>
                )}
            </TableBody>
        </Table>
    )
}
