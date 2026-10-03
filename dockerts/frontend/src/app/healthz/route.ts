import { BACKEND_UNREACHABLE, backendUrl } from "@/lib/backend";

/** Avoid build-time rendering; health is evaluated for each request. */
export const dynamic = "force-dynamic";

export async function GET(): Promise<Response> {
  try {
    const upstream = await fetch(`${backendUrl()}/healthz`, { cache: "no-store" });
    const body = await upstream.json();
    return Response.json(body, { status: upstream.status });
  } catch {
    return Response.json(
      {
        ...BACKEND_UNREACHABLE,
        status: "error",
        backend: "error",
      },
      { status: 503 },
    );
  }
}