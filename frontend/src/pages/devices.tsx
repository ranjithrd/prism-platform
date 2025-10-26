import {
	Button,
	Modal,
	ModalBody,
	ModalContent,
	ModalHeader,
	useDisclosure,
} from "@heroui/react"
import Devices from "../components/Devices"
import { Layout } from "../components/Layout"
import { EditDevice } from "../components/EditDevice"
import {
	createDeviceV1ApiDevicesPost,
	editDeviceV1ApiDevicesDeviceIdEditPost,
	getGetDevicesV1ApiDevicesGetKey,
} from "../api/api-client"
import { autoToast } from "../components/toast"
import { mutate } from "swr"
import { useState } from "react"
import type { Device } from "../api/schemas"

const EMPTY_DEVICE = {
	device_id: "",
	device_name: "",
	device_uuid: "",
}

export default function DevicesPage() {
	const { onOpen, onClose, isOpen } = useDisclosure()
	const [editingDevice, setEditingDevice] = useState<{
		device_id: string
		device_name: string
		device_uuid: string
	}>(EMPTY_DEVICE)

	function handleAdd(onClose: () => void) {
		return async (data: { device_name: string; device_uuid: string }) => {
			await autoToast(
				createDeviceV1ApiDevicesPost({
					device_name: data.device_name,
					device_uuid: data.device_uuid,
				}),
				{
					loadingText: "Adding device...",
					successText: "Device added successfully.",
					errorText: "Failed to add device.",
				}
			)
			await mutate(getGetDevicesV1ApiDevicesGetKey())
			onClose()
		}
	}

	function handleEdit(onClose: () => void) {
		return async (data: { device_name: string; device_uuid: string }) => {
			await autoToast(
				editDeviceV1ApiDevicesDeviceIdEditPost(
					editingDevice.device_id!,
					{
						device_name: data.device_name,
						device_uuid: data.device_uuid,
					}
				),
				{
					loadingText: "Saving device...",
					successText: "Device saved successfully.",
					errorText: "Failed to save device.",
				}
			)
			await mutate(getGetDevicesV1ApiDevicesGetKey())
			onClose()
		}
	}

	function openEditModal(device: Device) {
		setEditingDevice({
			device_id: device.device_id!,
			device_name: device.device_name ?? "",
			device_uuid: device.device_uuid ?? "",
		})
		onOpen()
	}

	return (
		<Layout>
			<div className="flex flex-col gap-2 md:flex-row md:justify-between md:items-center">
				<h1 className="text-2xl font-bold">Devices</h1>
				<Button
					color="primary"
					onPress={() => {
						setEditingDevice(EMPTY_DEVICE)
						onOpen()
					}}
				>
					Add Device
				</Button>
			</div>
			<div className="h-4"></div>
			<Devices onEdit={openEditModal} />
			<Modal isOpen={isOpen} onClose={onClose}>
				<ModalContent>
					{(onClose) => (
						<>
							<ModalHeader>
								<h3 className="text-lg font-semibold">
									Add Device
								</h3>
							</ModalHeader>
							<ModalBody className="flex flex-col mb-4">
								<EditDevice
									device={editingDevice}
									onSave={
										editingDevice.device_id
											? handleEdit(onClose)
											: handleAdd(onClose)
									}
								/>
							</ModalBody>
						</>
					)}
				</ModalContent>
			</Modal>
		</Layout>
	)
}
