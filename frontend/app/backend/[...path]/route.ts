import { proxyRequest } from "../../../lib/backend-proxy.mjs";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";
type RouteContext = { params: Promise<{ path: string[] }> };

async function handle(request: Request, context: RouteContext) {
  const { path = [] } = await context.params;
  return proxyRequest(request, path);
}

export const GET = handle;
export const POST = handle;
