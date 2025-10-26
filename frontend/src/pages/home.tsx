import { ArrowRightIcon } from "@heroicons/react/20/solid"
import Devices from "../components/Devices"
import Hosts from "../components/Hosts"
import { Layout } from "../components/Layout"
import RecentConfigurations from "../components/RecentConfigurations"
import { Link } from "wouter"
import { RecentTraces } from "../components/RecentTraces"
import ResponsiveGrid from "../components/ResponsiveGrid"
import BigButton from "../components/BigButton"

export default function HomePage() {
	return (
		<Layout>
			{/* <h1 className="text-2xl font-bol">
				Welcome
			</h1> */}
			<h2 className="text-xl font-bold">Actions</h2>
			<div className="h-4"></div>
			<ResponsiveGrid>
				<Link href="/queries">
					<BigButton>
						Manage Queries{" "}
						<ArrowRightIcon className="inline size-5" />
					</BigButton>
				</Link>
				<Link href="/groupQuery">
					<BigButton>
						Analyze Traces{" "}
						<ArrowRightIcon className="inline size-5" />
					</BigButton>
				</Link>
				<Link href="/trace">
					<BigButton>
						Take a Trace{" "}
						<ArrowRightIcon className="inline size-5" />
					</BigButton>
				</Link>
			</ResponsiveGrid>
			<div className="h-6"></div>
			<RecentConfigurations />
			<div className="h-6"></div>
			<Link href="/traces">
				<h2 className="text-xl font-bold">
					Recent Traces <ArrowRightIcon className="inline size-4" />
				</h2>
			</Link>
			<RecentTraces />
			<div className="h-6"></div>
			<Link href="/devices">
				<h2 className="text-xl font-bold">
					Devices <ArrowRightIcon className="inline size-4" />
				</h2>
			</Link>
			<div className="h-4"></div>
			<Devices />
			<div className="h-6"></div>
			<h2 className="text-xl font-bold">Hosts</h2>
			<div className="h-4"></div>
			<Hosts />
		</Layout>
	)
}
