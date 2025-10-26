import Axios, { type AxiosRequestConfig } from "axios"

const API_URL = import.meta.env.VITE_PUBLIC_API_URL || "http://localhost:8000"

/**
 * This is the main Axios instance.
 * Renamed to AXIOS_INSTANCE to be used by the customInstance function.
 */
export const AXIOS_INSTANCE = Axios.create({
	baseURL: API_URL,
	headers: {
		"Content-Type": "application/json",
	},
	withCredentials: true,
})

AXIOS_INSTANCE.interceptors.response.use(
	(response) => {
		// Return the data directly
		return response.data
	},
	(error) => {
		// Handle errors globally
		return Promise.reject(error)
	}
)

export default function customInstance<T>(
	config: AxiosRequestConfig,
	options?: AxiosRequestConfig
): Promise<T> {
	const source = Axios.CancelToken.source()
	const promise = AXIOS_INSTANCE({
		...config,
		...options,
		cancelToken: source.token,
	}).then((data) => data as T)

	return promise
}
