import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

/**
 * Standard shadcn-style class merger. Use everywhere variants meet user-supplied
 * className props.
 */
export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}
