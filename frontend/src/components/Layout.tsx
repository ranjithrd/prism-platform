export function Layout({ children }: { children: React.ReactNode }) {
	return (
		<div className="flex flex-col w-full max-w-5xl px-6 py-6  [overflow-clip-margin:1rem]">
			{children}
		</div>
	)
}
