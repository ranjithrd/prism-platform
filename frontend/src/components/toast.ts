import { addToast, closeToast } from "@heroui/react"

export function autoToastError(errorText: string, toast: string | null) {
	if (toast) closeToast(toast)
	addToast({
		title: errorText || "Error!",
		icon: "danger",
		color: "danger",
	})
}

export function autoToastSuccess(successText: string, toast: string | null) {
	if (toast) closeToast(toast)
	addToast({
		title: successText || "Success!",
	})
}

export const apiErrorFunction = <T extends { error?: string | null }>(
	data: T
) => data?.error !== null && data.error !== undefined

export function autoToast<T>(
	promise: Promise<T>,
	{
		errorFunction,
		errorText,
		successText,
		loadingText,
	}: {
		errorFunction?: ((d: T) => boolean) | null
		successText?: string
		loadingText?: string
		errorText?: string
	}
): Promise<T> {
	const t = addToast({
		title: loadingText || "Loading...",
		promise,
	})

	promise
		.then((data) => {
			if (errorFunction && errorFunction(data)) {
				autoToastError(errorText || "Error!", t)
			} else {
				autoToastSuccess(successText || "Success!", t)
			}
		})
		.catch(() => {
			autoToastError(errorText || "Error!", t)
		})

	return promise
}
