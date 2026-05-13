"use client";

import { forwardRef } from "react";
import clsx from "clsx";

export type CheckboxProps = Omit<
  React.InputHTMLAttributes<HTMLInputElement>,
  "type"
> & {
  label: React.ReactNode;
  error?: string;
};

export const Checkbox = forwardRef<HTMLInputElement, CheckboxProps>(
  function Checkbox({ label, error, className, id, ...rest }, ref) {
    const inputId = id ?? rest.name;
    return (
      <label
        htmlFor={inputId}
        className="flex cursor-pointer items-start gap-3 text-sm text-zinc-700"
      >
        <input
          ref={ref}
          id={inputId}
          type="checkbox"
          className={clsx(
            "mt-0.5 size-4 rounded border-zinc-300 text-brand-600 focus:ring-2 focus:ring-brand-500/30",
            className
          )}
          aria-invalid={!!error}
          {...rest}
        />
        <span className="flex-1 leading-relaxed">{label}</span>
      </label>
    );
  }
);
