import { InlineQueries } from "../components/InlineQueries"
import { Layout } from "../components/Layout"

export default function QueriesPage() {
	return (
		<Layout>
			<h1 className="text-2xl font-bold">Queries</h1>
            <div className="h-4"></div>
			<InlineQueries limit={1_000_000_000} />
		</Layout>
	)
}
