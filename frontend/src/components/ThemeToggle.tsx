"use client";
import { ThemeIcon } from "./icons";

/* Toggles the explicit [data-theme] attribute on <html>, overriding the OS
   preference. Matches the mockups' theme button. */
export function ThemeToggle() {
  function toggle() {
    const root = document.documentElement;
    const current =
      root.getAttribute("data-theme") ??
      (window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
    root.setAttribute("data-theme", current === "dark" ? "light" : "dark");
  }
  return (
    <button type="button" className="btn btn-ghost" onClick={toggle} aria-label="Toggle dark mode">
      <ThemeIcon />
      Theme
    </button>
  );
}
