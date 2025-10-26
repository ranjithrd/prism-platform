import { defineConfig } from "orval"

export default defineConfig({
	api: {
		input: "./openapi.json", // The local file fetched by our script
		output: {
			target: "./src/api/api-client.ts", // Single file output for all hooks and models
			schemas: "./src/api/schemas", // This will be ignored due to single file output, but good practice
			client: "swr", // We want SWR hooks
			mode: "single", // Generate a single file
			override: {
				/**
				 * Tell Orval how to import our custom axios instance.
				 */
				mutator: {
					path: "./src/api/axios.ts", // Path to our custom instance
					name: "axiosInstance", // Name of the exported variable
					default: true, // Use 'export default'
				},
			},
		},
	},
})
