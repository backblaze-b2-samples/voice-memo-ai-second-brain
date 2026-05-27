"use client";

interface TagChipProps {
  label: string;
  variant?: "default" | "topic" | "entity";
}

/**
 * Single-color chip used to render LLM-extracted tags on memo cards and
 * the detail page. Variants tint the chip lightly so a memo with both
 * tags and topics still reads as a coherent row.
 */
export function TagChip({ label, variant = "default" }: TagChipProps) {
  const palette: Record<string, string> = {
    default: "bg-secondary text-secondary-foreground",
    topic: "bg-primary/10 text-primary",
    entity: "bg-accent text-accent-foreground",
  };
  return (
    <span
      className={`inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-medium ${palette[variant]}`}
    >
      {label}
    </span>
  );
}
