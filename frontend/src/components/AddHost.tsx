import {
	Button,
	Input,
	Modal,
	ModalBody,
	ModalContent,
	ModalHeader,
	useDisclosure,
} from "@heroui/react"
import { useState } from "react"

export default function AddHost({
	onAdd,
}: {
	onAdd: (hostname: string, onClose: () => void) => void
}) {
	const [hostname, setHostname] = useState<string>("")
	const { isOpen, onOpen, onClose } = useDisclosure()

	return (
		<>
			{!isOpen ? (
				<Button
					className="mt-4 w-min"
					size="sm"
					variant="bordered"
					onPress={onOpen}
				>
					Add a Worker
				</Button>
			) : null}
			<Modal isOpen={isOpen} onClose={onClose}>
				<ModalContent>
					{(onClose) => (
						<>
							<ModalHeader>
								<h3 className="text-xl font-semibold">
									Add a Worker
								</h3>
							</ModalHeader>
							<ModalBody className="flex flex-col gap-4 mb-4">
								<Input
									label="Worker Hostname"
									value={hostname}
									onValueChange={setHostname}
									placeholder="e.g., worker_1"
									labelPlacement="outside"
									size="md"
								/>
								<Button
									color="primary"
									onPress={() => {
										onAdd(hostname, onClose)
									}}
								>
									Add Worker
								</Button>
							</ModalBody>
						</>
					)}
				</ModalContent>
			</Modal>
		</>
	)
}
