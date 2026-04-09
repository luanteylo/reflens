import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

const PUBLIC_PATHS = ["/login", "/signup", "/verify-email"];

export function middleware(request: NextRequest) {
  // Skip auth check if not enabled
  if (process.env.NEXT_PUBLIC_AUTH_ENABLED?.toLowerCase() !== "true") {
    return NextResponse.next();
  }

  const { pathname } = request.nextUrl;

  // Allow public paths
  if (PUBLIC_PATHS.some((p) => pathname.startsWith(p))) {
    return NextResponse.next();
  }

  // Check for access_token cookie
  const token = request.cookies.get("access_token");
  if (!token) {
    return NextResponse.redirect(new URL("/login", request.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico|api).*)"],
};
