import { clerkMiddleware, createRouteMatcher } from '@clerk/nextjs/server';
import { NextResponse } from 'next/server';

const isProtectedRoute = createRouteMatcher(['/dashboard(.*)', '/settings(.*)']);
const isPackageRoute = createRouteMatcher(['/choose-package(.*)']);

export default clerkMiddleware(async (auth, req) => {
  const { userId, redirectToSignIn } = await auth();
  const url = req.nextUrl.clone();

  if ((isProtectedRoute(req) || isPackageRoute(req)) && !userId) {
    return redirectToSignIn({ returnBackUrl: req.url });
  }

  if (userId && isProtectedRoute(req)) {
    const hasSelectedPackage = req.cookies.get('ls_has_selected_package')?.value === 'true';
    if (!hasSelectedPackage) {
      url.pathname = '/choose-package';
      url.searchParams.set('returnTo', req.nextUrl.pathname);
      return NextResponse.redirect(url);
    }
  }

  if (userId && isPackageRoute(req)) {
    const hasSelectedPackage = req.cookies.get('ls_has_selected_package')?.value === 'true';
    if (hasSelectedPackage) {
      url.pathname = '/dashboard/audit';
      url.search = '';
      return NextResponse.redirect(url);
    }
  }
});

export const config = {
  matcher: [
    '/((?!_next|[^?]*\\.(?:html?|css|js(?!on)|jpe?g|webp|png|gif|svg|ico|ttf|woff2?|csv|docx?|xlsx?|zip|webmanifest)).*)',
    '/(api|trpc)(.*)',
  ],
};
