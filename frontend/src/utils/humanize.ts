import dayjs from "dayjs"
import utc from "dayjs/plugin/utc"

dayjs.extend(utc)

export function toTitleCase(str: string | undefined): string | null {
	if (!str) return null

	return str.toLowerCase().replace(/\b\w/g, (char) => char.toUpperCase())
}

export function humanizeDate(
	dateString: string | undefined,
	showTime: boolean = false
): string {
	if (!dateString) return "N/A"
	// assume dateString is in UTC without a Z at the end
	if (!dateString.endsWith("Z") && !dateString.includes("+")) {
		dateString += "Z"
	}

	// this should also convert to local time
	return dayjs(dateString)
		.local()
		.format(showTime ? "MMM DD YYYY, h:mm A" : "MMM DD YYYY")
}
