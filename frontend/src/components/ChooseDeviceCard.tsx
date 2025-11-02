import { Button, Card, CardBody, CardFooter, Checkbox } from "@heroui/react"
import type { Device } from "../api/schemas"

export default function ChooseDeviceCard({
	device,
	isChosen,
	setIsChosen,
}: {
	device: Device
	isChosen: boolean
	setIsChosen: (isChosen: boolean) => void
}) {
	const isDisabled = device.last_status !== "online"

	return (
		<Card
			className={`p-2 ${""}`}
			isPressable
			onPress={() => {
				if (isDisabled) return
				setIsChosen(!isChosen)
			}}
			isDisabled={isDisabled}
		>
			<CardBody className="flex flex-col justify-center h-full gap-0">
				{isDisabled && (
					<p className="italic font-bold">This device is offline!</p>
				)}
				<p className="text-xl font-semibold">{device.device_name}</p>
				<p className="">{device.device_uuid}</p>
				<p className="">
					{device.host
						? `Last connected to ${device.host}`
						: "Disconnected"}
				</p>
			</CardBody>
			<CardFooter className="flex justify-end w-full">
				<Checkbox
					size="lg"
					className="items-end justify-end p-0 m-0"
					classNames={{
						wrapper: "p-0 m-0",
					}}
					isSelected={isChosen}
					onValueChange={() => {
						setIsChosen(!isChosen)
					}}
				/>
			</CardFooter>
		</Card>
	)
}
