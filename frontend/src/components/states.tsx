import { InboxIcon, WarnTriangle } from "./icons";

/* Explicit empty / error states (design acceptance rule #4). Each states what
   is missing or failed and the action to resolve it. */

export function EmptyState({ title, message }: { title: string; message: string }) {
  return (
    <div className="state-block" role="status">
      <InboxIcon />
      <div className="state-title">{title}</div>
      <p className="state-msg">{message}</p>
    </div>
  );
}

export function ErrorState({ title, message }: { title: string; message: string }) {
  return (
    <div className="state-block" role="alert">
      <WarnTriangle />
      <div className="state-title">{title}</div>
      <p className="state-msg">{message}</p>
    </div>
  );
}

/* Skeleton line/block for loading states (>300ms waits). */
export function Skeleton({ height = 16, width = "100%" }: { height?: number; width?: string | number }) {
  return <div className="skeleton" style={{ height, width }} aria-hidden />;
}
