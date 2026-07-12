import { type NextRequest, NextResponse } from "next/server";
import { createServerClient } from "@supabase/ssr";

export async function middleware(request: NextRequest) {
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const key = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
  const isLogin = request.nextUrl.pathname.startsWith("/login");
  const isPublic = isLogin || request.nextUrl.pathname.startsWith("/api/demo-login");

  // If Supabase env is not configured at runtime, don't hard-fail the whole
  // site — let pages render (the (app) layout still gates via its own check).
  if (!url || !key) return NextResponse.next();

  try {
    let response = NextResponse.next({ request });
    const supabase = createServerClient(url, key, {
      cookies: {
        getAll: () => request.cookies.getAll(),
        setAll: (list) => {
          list.forEach(({ name, value }) => request.cookies.set(name, value));
          response = NextResponse.next({ request });
          list.forEach(({ name, value, options }) =>
            response.cookies.set(name, value, options));
        },
      },
    });
    const { data: { user } } = await supabase.auth.getUser();
    if (!user && !isPublic) {
      return NextResponse.redirect(new URL("/login", request.url));
    }
    if (user && isLogin) {
      return NextResponse.redirect(new URL("/", request.url));
    }
    return response;
  } catch {
    // Never turn a transient auth/network error into a site-wide 500.
    return NextResponse.next();
  }
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico|.*\\.png$).*)"],
};
