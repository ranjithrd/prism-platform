import { CodeEditor } from "./CodeEditor"

export default function BpftraceConfigInput({
	configText,
	setConfigText,
}: {
	configText: string
	setConfigText: (text: string) => void
}) {
	return (
		<div className="flex flex-col gap-2">
			<p className="text-sm text-default-500">
				Enter your bpftrace script (.bt format). The script will run on
				the Android device using eadb.
			</p>
			<details className="mb-2">
				<summary className="text-sm font-medium cursor-pointer text-default-700 hover:text-default-900">
					Common bpftrace examples
				</summary>
				<div className="p-3 mt-2 space-y-2 text-xs rounded-lg bg-default-100">
					<div>
						<p className="font-semibold text-default-900">
							Count system calls by process name:
						</p>
						<code className="block p-2 mt-1 rounded bg-default-200">
							tracepoint:raw_syscalls:sys_enter &#123; @[comm] = count(); &#125;
						</code>
					</div>
					<div>
						<p className="font-semibold text-default-900">
							List probes containing sleep:
						</p>
						<code className="block p-2 mt-1 rounded bg-default-200">
							kprobe:do_nanosleep &#123; printf("PID %d sleeping...\n", pid); &#125
						</code>
					</div>
				</div>
			</details>
			<CodeEditor value={configText} onValueChange={setConfigText} />
			<div className="p-3 mt-2 text-xs border rounded-lg bg-warning-50 dark:bg-warning-100/10 border-warning-200 dark:border-warning-500/20">
				<p className="mb-1 font-semibold text-warning-800 dark:text-warning-600">
					⚠️ Setup Required (Worker GUI):
				</p>
				<ol className="space-y-1 list-decimal list-inside text-warning-700 dark:text-warning-600">
					<li>
						Click <strong>"Install eadb"</strong> (once, global
						setup)
					</li>
					<li>
						For each device: Click <strong>"Set up bpftrace"</strong>{" "}
						button on the device card
					</li>
				</ol>
				<p className="mt-2 text-warning-700 dark:text-warning-600">
					<strong>Note:</strong> Requires root access.
				</p>
			</div>
		</div>
	)
}
