import { useEffect, useState } from "react"
import { AXIOS_INSTANCE } from "./axios"

export interface StreamEvent {
	device_serial: string
	status: string
	message: string
	timestamp: string
	trace_id?: string
}

export function useJobResultStream(jobId: string) {
	const [stream, setStream] = useState<StreamEvent[]>([])
	const [isConnected, setIsConnected] = useState<boolean>(false)

	useEffect(() => {
		const eventSource = new EventSource(
			`${AXIOS_INSTANCE.defaults.baseURL}/v1/api/requests/${jobId}/stream`,
			{
				withCredentials: true,
			}
		)

		eventSource.onopen = () => {
			setIsConnected(true)
		}

		eventSource.onmessage = (event) => {
			const newEvent = JSON.parse(event.data)

			console.log("Received event:", newEvent)

			if (newEvent.device_serial && newEvent.timestamp) {
				setStream((prevStream) => [newEvent, ...prevStream])
			}
		}

		eventSource.onerror = () => {
			setIsConnected(false)
			eventSource.close()
		}

		return () => {
			eventSource.close()
		}
	}, [jobId])

	return { stream, isConnected }
}
