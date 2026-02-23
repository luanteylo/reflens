"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  FileText,
  Home,
  Search,
  Tags,
  Upload,
  Users,
} from "lucide-react";
import { clsx } from "clsx";

const NAV = [
  { href: "/", label: "Dashboard", icon: Home },
  { href: "/papers", label: "Papers", icon: FileText },
  { href: "/upload", label: "Upload", icon: Upload },
  { href: "/search", label: "Search", icon: Search },
  { href: "/tags", label: "Tags", icon: Tags },
  { href: "/authors", label: "Authors", icon: Users },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="fixed inset-y-0 left-0 z-30 flex w-56 flex-col border-r border-border bg-card">
      <div className="flex h-14 items-center gap-2 border-b border-border px-4">
        <FileText className="h-6 w-6 text-primary" />
        <span className="text-lg font-semibold">RefLens</span>
      </div>
      <nav className="flex-1 space-y-1 px-2 py-4">
        {NAV.map(({ href, label, icon: Icon }) => {
          const active = href === "/" ? pathname === "/" : pathname.startsWith(href);
          return (
            <Link
              key={href}
              href={href}
              className={clsx(
                "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                active
                  ? "bg-accent text-accent-foreground"
                  : "text-muted-foreground hover:bg-muted hover:text-foreground"
              )}
            >
              <Icon className="h-4 w-4" />
              {label}
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}
