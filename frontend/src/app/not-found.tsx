import { LinkButton } from "@/shared/ui";
import { routes } from "@/shared/config";

export default function NotFound() {
  return (
    <div className="mx-auto flex max-w-md flex-col items-center py-20 text-center">
      <p className="text-sm font-semibold text-[var(--brand)]">404</p>
      <h1 className="mt-2 text-3xl font-extrabold tracking-tight text-slate-900">Page not found</h1>
      <p className="mt-3 text-[var(--text-secondary)]">
        The page you are looking for does not exist or has moved.
      </p>
      <LinkButton href={routes.dashboard()} className="mt-6">Back to home</LinkButton>
    </div>
  );
}
