import {
    CheckIcon,
    ClipboardIcon,
    ChevronDownIcon,
    ChevronUpIcon,
} from "@heroicons/react/20/solid"
import { Button, Tooltip } from "@heroui/react"
import { useState, useRef, useEffect } from "react"

// Define your minimum collapsed height in pixels
const MIN_COLLAPSED_HEIGHT = 100

export default function CodeView({
    children,
    fullText,
}: {
    children: React.ReactNode
    fullText: string
}) {
    const [isCopied, setIsCopied] = useState(false)
    const [isExpanded, setIsExpanded] = useState(false)
    const [isOverflowing, setIsOverflowing] = useState(false)
    const contentRef = useRef<HTMLParagraphElement>(null)

    const handleCopy = async () => {
        if (!navigator.clipboard) return
        try {
            await navigator.clipboard.writeText(fullText)
            setIsCopied(true)
            setTimeout(() => setIsCopied(false), 2000)
        } catch (err) {
            console.error("Failed to copy text: ", err)
        }
    }

    // Check if the content is taller than the minimum height
    useEffect(() => {
        if (contentRef.current) {
            // Check if the content's full height exceeds our minimum
            setIsOverflowing(
                contentRef.current.scrollHeight > MIN_COLLAPSED_HEIGHT
            )
        }
        // Re-check whenever the content changes
    }, [children])

    return (
        <div className="relative border rounded-lg border-default-200 bg-default-50">
            {/* Copy Button */}
            <Tooltip
                content={isCopied ? "Copied!" : "Copy config"}
                placement="top"
            >
                <Button
                    isIconOnly
                    size="sm"
                    className="absolute z-10 right-2 top-2 text-default-500"
                    onPress={handleCopy}
                >
                    {isCopied ? (
                        <CheckIcon className="w-5 h-5 text-green-500" />
                    ) : (
                        <ClipboardIcon className="w-5 h-5" />
                    )}
                </Button>
            </Tooltip>

            {/* Collapsible Content Area */}
            <div
                className="overflow-hidden transition-all duration-300 ease-in-out"
                // Set max-height dynamically
                style={{
                    maxHeight: isExpanded
                        ? "1000px" // Arbitrary large value for expansion
                        : `${MIN_COLLAPSED_HEIGHT}px`,
                }}
            >
                <p
                    ref={contentRef}
                    className="p-2 pr-12 font-mono text-sm whitespace-pre-wrap wrap-break-word"
                >
                    {children}
                </p>
            </div>

            {/* Show More/Less Button */}
            {isOverflowing && (
                <div className="flex justify-center border-t border-default-200">
                    <Button
                        variant="light"
                        size="sm"
                        onPress={() => setIsExpanded(!isExpanded)}
                        // Make button full-width and remove top rounded corners
                        className="w-full h-8 rounded-t-none text-default-600"
                    >
                        {isExpanded ? "Show less" : "Show more"}
                        {isExpanded ? (
                            <ChevronUpIcon className="w-4 h-4 ml-1" />
                        ) : (
                            <ChevronDownIcon className="w-4 h-4 ml-1" />
                        )}
                    </Button>
                </div>
            )}
        </div>
    )
}