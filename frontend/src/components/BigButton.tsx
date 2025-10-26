import { Card, CardBody } from "@heroui/react"

export default function BigButton({
	children,
	classNames = {},
	onPress,
}: {
	children: React.ReactNode
	classNames?: {
		base?: string
		body?: string
		title?: string
	}
	onPress?: () => void
}) {
	return (
		<Card
			className={`p-4 w-full ${classNames.base || ""}`}
			isPressable
			onPress={onPress}
		>
			<CardBody
				className={`h-full flex-col justify-end ${
					classNames.body || ""
				}`}
			>
				<h2 className={`text-xl ${classNames.title || ""}`}>
					{children}
				</h2>
			</CardBody>
		</Card>
	)
}
