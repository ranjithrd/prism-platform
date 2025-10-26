import {
	Button,
	Navbar,
	NavbarBrand,
	NavbarContent,
	NavbarItem,
	NavbarMenu,
	NavbarMenuItem,
	NavbarMenuToggle,
} from "@heroui/react"
import { useState } from "react"
import { Link } from "wouter"

export default function AppNavbar() {
	const [isMenuOpen, setIsMenuOpen] = useState(false)

	const items = [
		// { name: "Home", path: "/" },
		{ name: "Devices", path: "/devices" },
		{ name: "Configurations", path: "/configurations" },
		{ name: "Traces", path: "/traces" },
		{ name: "Queries", path: "/queries" },
		{ name: "Analysis", path: "/groupQuery" },
	]

	return (
		<Navbar
			maxWidth="lg"
			classNames={{
				base: "py-2 bg-sky-700 text-white shadow-lg",
			}}
		>
			<NavbarContent justify="start">
				<NavbarMenuToggle
					aria-label={isMenuOpen ? "Close menu" : "Open menu"}
					className="sm:hidden"
					onClick={() => setIsMenuOpen(!open)}
				/>
				<Link href="/">
					<NavbarBrand className="text-xl font-bold">
						PRISM Platform
					</NavbarBrand>
				</Link>
			</NavbarContent>
			<NavbarContent className="hidden gap-4 sm:flex" justify="end">
				{items.map((item) => (
					<NavbarItem key={item.path}>
						<Link href={item.path}>{item.name}</Link>
					</NavbarItem>
				))}
				<NavbarItem>
					<Button
						as={Link}
						to="/trace"
						variant="solid"
						className="font-bold bg-white text-primary-800"
					>
						Start Trace
					</Button>
				</NavbarItem>
			</NavbarContent>
			<NavbarMenu className="flex flex-col gap-4 py-6 pt-12 md:hidden">
				{items.map((item) => (
					<NavbarMenuItem key={item.path}>
						<Link href={item.path}>{item.name}</Link>
					</NavbarMenuItem>
				))}
				<Button
					as={Link}
					to="/trace"
					color="primary"
					size="lg"
					variant="bordered"
					className="mt-4 font-bold"
				>
					Start Trace
				</Button>
			</NavbarMenu>
		</Navbar>
	)
}
