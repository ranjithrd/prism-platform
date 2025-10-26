import { Route, Switch } from "wouter"
import HomePage from "./pages/home"
import { HeroUIProvider, ToastProvider } from "@heroui/react"
import AppNavbar from "./components/Navbar"
import { ConfigurationsViewPage } from "./pages/configurations/view"
import StartTracePage from "./pages/startTrace"
import JobPage from "./pages/job"
import AllConfigurationsPage from "./pages/configurations/all"
import AllTracesPage from "./pages/traces/all"
import DevicesPage from "./pages/devices"
import TracesViewPage from "./pages/traces/view"
import QueriesPage from "./pages/queries"
import GroupQueryPage from "./pages/groupQuery"

export default function App() {
	return (
		<HeroUIProvider>
			<div className="flex flex-col items-center w-screen h-screen overflow-x-hidden overscroll-none">
				<AppNavbar />
				<main className="flex flex-row justify-center w-full p-4 grow">
					<Switch>
						<Route path="/" component={HomePage} />

						<Route
							path="/configurations"
							component={AllConfigurationsPage}
						/>
						<Route path="/configurations/:id">
							{(params) => (
								// @ts-expect-error: params.id is string | undefined
								<ConfigurationsViewPage id={params.id} />
							)}
						</Route>

						<Route path="/trace" component={StartTracePage} />
						<Route path="/job/:id">
							{/* @ts-expect-error: params.id is string | undefined */}
							{(params) => <JobPage jobId={params.id} />}
						</Route>

						<Route path="/traces" component={AllTracesPage} />
						<Route path="/traces/:id">
							{/* @ts-expect-error: params.id is string | undefined */}
							{(params) => <TracesViewPage id={params.id ?? 0} />}
						</Route>

						<Route path="/devices" component={DevicesPage} />
						<Route path="/queries" component={QueriesPage} />
						<Route path="/groupQuery" component={GroupQueryPage} />
					</Switch>
				</main>
			</div>
			<ToastProvider />
		</HeroUIProvider>
	)
}
