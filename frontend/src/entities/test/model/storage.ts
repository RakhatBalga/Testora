/**
 * localStorage prefix for an in-progress exam. Scoped by username so two people
 * sharing a browser never see each other's answers or "in progress" badges.
 */
export function examStorageKey(type: string, username: string | null | undefined, id: number): string {
  return `${type}-${username ?? "anonymous"}-${id}`;
}
