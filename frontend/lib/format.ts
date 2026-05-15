/**
 * Format a chat ID with leading zeros (e.g., 1 -> "001", 67 -> "067")
 */
export function formatChatId(id: number): string {
  return id.toString().padStart(3, "0");
}

/**
 * Parse a formatted chat ID back to a number
 */
export function parseChatId(formattedId: string): number {
  return parseInt(formattedId, 10);
}
