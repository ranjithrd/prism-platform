import type React from "react"

export default function ResponsiveGrid({
	children,
	className = "",
	size = "medium",
}: {
	children: React.ReactNode
	className?: string
	size?: "small" | "medium" | "large"
}) {
	let cols = ""
	switch (size) {
		case "small":
			cols = "sm:grid-cols-2 md:grid-cols-4 lg:grid-cols-4 xl:grid-cols-4"
			break
		case "medium":
			cols = "sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-3 xl:grid-cols-3"
			break
		case "large":
			cols = "sm:grid-cols-1 md:grid-cols-2 lg:grid-cols-2 xl:grid-cols-2"
			break
	}
	
	return (
		<div
			className={`grid w-full grid-cols-1 gap-4 ${cols} ${className}`}
		>
			{children}
		</div>
	)
}
