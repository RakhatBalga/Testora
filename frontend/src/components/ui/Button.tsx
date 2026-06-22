import Link from "next/link";
import { ButtonHTMLAttributes, ReactNode } from "react";

type Variant = "primary" | "secondary" | "ghost";
type Size = "sm" | "md" | "lg";

const base =
  "inline-flex items-center justify-center gap-2 rounded-xl font-semibold transition focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500/40 disabled:cursor-not-allowed disabled:opacity-50";

const variants: Record<Variant, string> = {
  primary:
    "bg-blue-600 text-white shadow-sm shadow-blue-600/20 hover:bg-blue-700 active:bg-blue-800",
  secondary:
    "border border-slate-200 bg-white text-slate-700 hover:border-slate-300 hover:bg-slate-50",
  ghost: "text-slate-600 hover:bg-slate-100 hover:text-slate-900",
};

const sizes: Record<Size, string> = {
  sm: "px-3 py-1.5 text-sm",
  md: "px-4 py-2.5 text-sm",
  lg: "px-6 py-3 text-base",
};

function classes(variant: Variant, size: Size, className: string) {
  return `${base} ${variants[variant]} ${sizes[size]} ${className}`;
}

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: Variant;
  size?: Size;
};

export function Button({
  variant = "primary",
  size = "md",
  className = "",
  ...props
}: ButtonProps) {
  return <button className={classes(variant, size, className)} {...props} />;
}

type LinkButtonProps = {
  href: string;
  children: ReactNode;
  variant?: Variant;
  size?: Size;
  className?: string;
};

export function LinkButton({
  href,
  children,
  variant = "primary",
  size = "md",
  className = "",
}: LinkButtonProps) {
  return (
    <Link href={href} className={classes(variant, size, className)}>
      {children}
    </Link>
  );
}
