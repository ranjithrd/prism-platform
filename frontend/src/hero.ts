// hero.ts
import { heroui } from "@heroui/react"

const tailwindSkyTheme = {
	100: "#dff2fe",
	200: "#b8e6fe",
	300: "#74d4ff",
	400: "#00bcff",
	500: "#00a6f4", 
	600: "#0084d1",
	700: "#0069a8", 
	800: "#00598a",
	900: "#024a70",
	foreground: "#ffffff",
	DEFAULT: "#0069a8",
}

export default heroui({
	themes: {
		light: {
			colors: {
				primary: tailwindSkyTheme,
			},
		},
		dark: {
			colors: {
				primary: tailwindSkyTheme,
			},
		},
	},
})
